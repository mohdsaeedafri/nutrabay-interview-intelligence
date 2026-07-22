const QUESTION_SHEET = 'Question_Sets';
const RESPONSE_SHEET = 'Responses';
const CONFIG_SHEET = 'Config';
const CATEGORIES = ['Intent', 'Quant Ability', 'Job Competency', 'Core Competency', 'EQ'];
const CATEGORY_WEIGHTS = {
  'Intent': 10,
  'Quant Ability': 20,
  'Job Competency': 30,
  'Core Competency': 25,
  'EQ': 15
};

const QUESTION_HEADERS = [
  'question_set_id', 'role_title', 'created_at', 'source_jd_hash', 'position',
  'question_id', 'category', 'question_text', 'is_active'
];

const RESPONSE_HEADERS = (() => {
  const headers = [
    'timestamp', 'submission_id', 'question_set_id', 'role_title',
    'candidate_name', 'raw_total', 'raw_max', 'weighted_percent'
  ];
  for (let index = 1; index <= 15; index += 1) {
    const prefix = `q${String(index).padStart(2, '0')}`;
    headers.push(`${prefix}_category`, `${prefix}_question`, `${prefix}_score`, `${prefix}_notes`);
  }
  return headers;
})();


function setupSpreadsheet() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  if (!spreadsheet) {
    throw new Error('Run setupSpreadsheet from the Apps Script project bound to the target Google Sheet.');
  }
  PropertiesService.getScriptProperties().setProperty('SPREADSHEET_ID', spreadsheet.getId());
  ensureSheets_(spreadsheet);
  return {
    ok: true,
    spreadsheetId: spreadsheet.getId(),
    sheets: [QUESTION_SHEET, RESPONSE_SHEET, CONFIG_SHEET]
  };
}


function doGet(e) {
  const template = HtmlService.createTemplateFromFile('Index');
  const requestedId = String((e && e.parameter && e.parameter.questionSetId) || '');
  template.questionSetId = isUuid_(requestedId) ? requestedId : '';
  return template.evaluate()
    .setTitle('Nutrabay Interview Scorecard')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}


function doPost(e) {
  try {
    const raw = e && e.postData && e.postData.contents;
    if (!raw) throw publicError_('The request body is empty.');
    const payload = JSON.parse(raw);
    if (payload.action !== 'upsertQuestionSet') throw publicError_('Unsupported integration action.');

    const expectedToken = PropertiesService.getScriptProperties().getProperty('INTEGRATION_TOKEN') || '';
    if (expectedToken.length < 32) throw new Error('INTEGRATION_TOKEN is not configured.');
    if (!constantTimeEqual_(String(payload.integrationToken || ''), expectedToken)) {
      throw publicError_('The integration token is invalid.');
    }

    const result = upsertQuestionSet_(payload);
    return jsonOutput_(result);
  } catch (error) {
    console.error('doPost failed', error && error.stack ? error.stack : error);
    return jsonOutput_({
      ok: false,
      message: error && error.isPublic ? error.message : 'The scoring service could not process the question set.'
    });
  }
}


function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}


function getQuestionSet(questionSetId) {
  const id = String(questionSetId || '').trim();
  if (!isUuid_(id)) throw new Error('This scoring link is missing a valid question-set ID.');
  const questionSet = getQuestionSet_(id);
  if (!questionSet) throw new Error('The approved question set was not found. Ask the hiring manager for a new link.');
  return questionSet;
}


function submitScore(payload) {
  const candidateName = String(payload && payload.candidateName || '').trim();
  const submissionId = String(payload && payload.submissionId || '').trim();
  const questionSetId = String(payload && payload.questionSetId || '').trim();
  const answers = payload && Array.isArray(payload.answers) ? payload.answers : [];

  if (candidateName.length < 2 || candidateName.length > 100) {
    throw new Error('Enter a candidate name between 2 and 100 characters.');
  }
  if (!isUuid_(submissionId)) throw new Error('The submission ID is invalid. Refresh the page and retry.');
  if (!isUuid_(questionSetId)) throw new Error('The question-set ID is invalid.');

  const questionSet = getQuestionSet_(questionSetId);
  if (!questionSet) throw new Error('The approved question set was not found.');
  if (answers.length !== questionSet.questions.length) {
    throw new Error('Every question must have exactly one score.');
  }

  const answerMap = {};
  answers.forEach((answer) => {
    const questionId = String(answer.questionId || '');
    if (answerMap[questionId]) throw new Error('A question was submitted more than once.');
    const score = Number(answer.score);
    const notes = String(answer.notes || '').trim();
    if (!Number.isInteger(score) || score < 1 || score > 5) {
      throw new Error('Every score must be a whole number from 1 to 5.');
    }
    if (notes.length > 2000) throw new Error('Notes must be 2,000 characters or fewer per question.');
    answerMap[questionId] = { score, notes };
  });

  const orderedAnswers = questionSet.questions.map((question) => {
    const answer = answerMap[question.id];
    if (!answer) throw new Error(`A score is missing for question ${question.position}.`);
    return { question, score: answer.score, notes: answer.notes };
  });
  if (Object.keys(answerMap).length !== questionSet.questions.length) {
    throw new Error('The submission contains an unknown question.');
  }

  const scores = calculateScores_(orderedAnswers);
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const spreadsheet = getSpreadsheet_();
    ensureSheets_(spreadsheet);
    const sheet = spreadsheet.getSheetByName(RESPONSE_SHEET);
    const existing = findSubmission_(sheet, submissionId);
    if (existing) {
      return { ok: true, duplicate: true, submissionId, message: 'This scorecard was already submitted.' };
    }

    const timestamp = new Date();
    const row = buildResponseRow_(
      timestamp,
      submissionId,
      questionSet,
      candidateName,
      orderedAnswers,
      scores
    );
    sheet.getRange(sheet.getLastRow() + 1, 1, 1, row.length).setValues([row]);
    return {
      ok: true,
      duplicate: false,
      submissionId,
      weightedPercent: scores.weightedPercent,
      rawTotal: scores.rawTotal,
      rawMax: scores.rawMax,
      submittedAt: timestamp.toISOString()
    };
  } finally {
    lock.releaseLock();
  }
}


function upsertQuestionSet_(payload) {
  const validated = validateQuestionSetPayload_(payload);
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const spreadsheet = getSpreadsheet_();
    ensureSheets_(spreadsheet);
    const sheet = spreadsheet.getSheetByName(QUESTION_SHEET);

    for (let row = sheet.getLastRow(); row >= 2; row -= 1) {
      if (String(sheet.getRange(row, 1).getValue()) === validated.questionSetId) {
        sheet.deleteRow(row);
      }
    }

    const rows = validated.questions.map((question) => [
      validated.questionSetId,
      escapeForSheet_(validated.roleTitle),
      new Date(validated.createdAt),
      validated.sourceJdHash,
      question.position,
      question.id,
      question.category,
      escapeForSheet_(question.text),
      true
    ]);
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, QUESTION_HEADERS.length).setValues(rows);

    const serviceUrl = ScriptApp.getService().getUrl();
    if (!serviceUrl) throw new Error('Deploy this project as a web app before publishing questions.');
    return {
      ok: true,
      questionSetId: validated.questionSetId,
      scoringUrl: `${serviceUrl}?questionSetId=${encodeURIComponent(validated.questionSetId)}`
    };
  } finally {
    lock.releaseLock();
  }
}


function getQuestionSet_(questionSetId) {
  const spreadsheet = getSpreadsheet_();
  ensureSheets_(spreadsheet);
  const sheet = spreadsheet.getSheetByName(QUESTION_SHEET);
  if (sheet.getLastRow() < 2) return null;
  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, QUESTION_HEADERS.length).getValues();
  const rows = values.filter((row) => String(row[0]) === questionSetId && row[8] === true);
  if (!rows.length) return null;
  rows.sort((a, b) => Number(a[4]) - Number(b[4]));
  return {
    questionSetId,
    roleTitle: String(rows[0][1]),
    createdAt: new Date(rows[0][2]).toISOString(),
    questions: rows.map((row) => ({
      position: Number(row[4]),
      id: String(row[5]),
      category: String(row[6]),
      text: String(row[7])
    }))
  };
}


function getSpreadsheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured. Run setupSpreadsheet once.');
  return SpreadsheetApp.openById(id);
}


function ensureSheets_(spreadsheet) {
  ensureSheet_(spreadsheet, QUESTION_SHEET, QUESTION_HEADERS);
  ensureSheet_(spreadsheet, RESPONSE_SHEET, RESPONSE_HEADERS);
  const config = ensureSheet_(spreadsheet, CONFIG_SHEET, ['key', 'value']);
  const configRows = [
    ['schema_version', '1.0'],
    ['category_order', CATEGORIES.join(' | ')],
    ['weight_intent', 10],
    ['weight_quant_ability', 20],
    ['weight_job_competency', 30],
    ['weight_core_competency', 25],
    ['weight_eq', 15],
    ['score_1', 'No evidence / poor'],
    ['score_2', 'Weak evidence'],
    ['score_3', 'Meets expectations'],
    ['score_4', 'Strong evidence'],
    ['score_5', 'Exceptional evidence']
  ];
  config.getRange(2, 1, configRows.length, 2).setValues(configRows);
}


function ensureSheet_(spreadsheet, name, headers) {
  const sheet = spreadsheet.getSheetByName(name) || spreadsheet.insertSheet(name);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.getRange(1, 1, 1, headers.length)
    .setBackground('#1E6B52')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold');
  sheet.setFrozenRows(1);
  return sheet;
}


function findSubmission_(sheet, submissionId) {
  if (sheet.getLastRow() < 2) return null;
  return sheet.getRange(2, 2, sheet.getLastRow() - 1, 1)
    .createTextFinder(submissionId)
    .matchEntireCell(true)
    .findNext();
}


function jsonOutput_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}


function publicError_(message) {
  const error = new Error(message);
  error.isPublic = true;
  return error;
}
