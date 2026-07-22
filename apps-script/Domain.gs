function validateQuestionSetPayload_(payload) {
  const questionSetId = String(payload.questionSetId || '').trim();
  const roleTitle = String(payload.roleTitle || '').trim();
  const sourceJdHash = String(payload.sourceJdHash || '').trim();
  const createdAt = String(payload.createdAt || '').trim();
  const questions = Array.isArray(payload.questions) ? payload.questions : [];

  if (!isUuid_(questionSetId)) throw publicError_('The question-set ID is invalid.');
  if (roleTitle.length < 2 || roleTitle.length > 160) throw publicError_('The role title is invalid.');
  if (!/^[a-f0-9]{64}$/.test(sourceJdHash)) throw publicError_('The JD fingerprint is invalid.');
  if (Number.isNaN(Date.parse(createdAt))) throw publicError_('The creation timestamp is invalid.');
  if (questions.length < 10 || questions.length > 15) throw publicError_('A question set must contain 10-15 questions.');

  const ids = {};
  const normalizedTexts = {};
  const categoryCounts = {};
  CATEGORIES.forEach((category) => { categoryCounts[category] = 0; });

  const validatedQuestions = questions.map((question, index) => {
    const id = String(question.id || '').trim();
    const position = Number(question.position);
    const category = String(question.category || '').trim();
    const text = String(question.text || '').replace(/\s+/g, ' ').trim();
    if (!isUuid_(id) || ids[id]) throw publicError_('Question IDs must be unique UUIDs.');
    if (!Number.isInteger(position) || position !== index + 1) {
      throw publicError_('Question positions must be consecutive and start at 1.');
    }
    if (!CATEGORIES.includes(category)) throw publicError_('A question has an invalid category.');
    if (text.length < 12 || text.length > 1200) throw publicError_('Every question must contain 12-1,200 characters.');
    const normalized = text.toLowerCase().replace(/[?.!\s]+$/g, '');
    if (normalizedTexts[normalized]) throw publicError_('Duplicate questions are not allowed.');
    ids[id] = true;
    normalizedTexts[normalized] = true;
    categoryCounts[category] += 1;
    return { id, position, category, text };
  });

  const missing = CATEGORIES.filter((category) => categoryCounts[category] === 0);
  if (missing.length) throw publicError_(`Every category is required. Missing: ${missing.join(', ')}.`);

  return { questionSetId, roleTitle, sourceJdHash, createdAt, questions: validatedQuestions };
}


function calculateScores_(orderedAnswers) {
  const categoryScores = {};
  CATEGORIES.forEach((category) => { categoryScores[category] = []; });
  let rawTotal = 0;
  orderedAnswers.forEach((entry) => {
    rawTotal += entry.score;
    categoryScores[entry.question.category].push(entry.score);
  });

  let weightedPercent = 0;
  CATEGORIES.forEach((category) => {
    const scores = categoryScores[category];
    if (!scores.length) throw new Error(`Cannot score a set without ${category}.`);
    const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    weightedPercent += (average / 5) * CATEGORY_WEIGHTS[category];
  });

  return {
    rawTotal,
    rawMax: orderedAnswers.length * 5,
    weightedPercent: Math.round((weightedPercent + Number.EPSILON) * 100) / 100
  };
}


function buildResponseRow_(timestamp, submissionId, questionSet, candidateName, orderedAnswers, scores) {
  const row = [
    timestamp,
    submissionId,
    questionSet.questionSetId,
    escapeForSheet_(questionSet.roleTitle),
    escapeForSheet_(candidateName),
    scores.rawTotal,
    scores.rawMax,
    scores.weightedPercent
  ];
  for (let index = 0; index < 15; index += 1) {
    const entry = orderedAnswers[index];
    if (entry) {
      row.push(
        entry.question.category,
        escapeForSheet_(entry.question.text),
        entry.score,
        escapeForSheet_(entry.notes)
      );
    } else {
      row.push('', '', '', '');
    }
  }
  if (row.length !== RESPONSE_HEADERS.length) throw new Error('Response row does not match the Sheet schema.');
  return row;
}


function escapeForSheet_(value) {
  const text = String(value == null ? '' : value);
  return /^[=+\-@]/.test(text) ? `'${text}` : text;
}


function isUuid_(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''));
}


function constantTimeEqual_(left, right) {
  const a = String(left || '');
  const b = String(right || '');
  let mismatch = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    mismatch |= (a.charCodeAt(index % Math.max(a.length, 1)) || 0) ^ (b.charCodeAt(index % Math.max(b.length, 1)) || 0);
  }
  return mismatch === 0;
}

