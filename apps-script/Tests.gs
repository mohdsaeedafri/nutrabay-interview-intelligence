function runAllTests() {
  const tests = [
    testEscapeForSheet_,
    testScoreCalculation_,
    testQuestionSetValidation_,
    testResponseRowShape_,
    testConstantTimeEqual_
  ];
  const results = [];
  tests.forEach((test) => {
    test();
    results.push({ name: test.name, status: 'passed' });
  });
  const summary = { ok: true, passed: results.length, results };
  console.log(JSON.stringify(summary));
  return summary;
}


function testEscapeForSheet_() {
  assertEqual_(escapeForSheet_('=SUM(A1:A2)'), "'=SUM(A1:A2)", 'Formula-like values must be escaped.');
  assertEqual_(escapeForSheet_('Normal note'), 'Normal note', 'Normal values must stay unchanged.');
}


function testScoreCalculation_() {
  const answers = CATEGORIES.map((category, index) => ({
    question: { category },
    score: index + 1
  }));
  const result = calculateScores_(answers);
  assertEqual_(result.rawTotal, 15, 'Raw total is wrong.');
  assertEqual_(result.rawMax, 25, 'Raw maximum is wrong.');
  assertEqual_(result.weightedPercent, 63, 'Weighted percentage is wrong.');
}


function testQuestionSetValidation_() {
  const questions = [];
  for (let index = 0; index < 10; index += 1) {
    questions.push({
      id: `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      position: index + 1,
      category: CATEGORIES[index % CATEGORIES.length],
      text: `Role-specific test question number ${index + 1}?`
    });
  }
  const payload = {
    questionSetId: '11111111-1111-4111-8111-111111111111',
    roleTitle: 'Senior Analyst - D2C Growth',
    sourceJdHash: 'a'.repeat(64),
    createdAt: new Date().toISOString(),
    questions
  };
  const result = validateQuestionSetPayload_(payload);
  assertEqual_(result.questions.length, 10, 'Ten valid questions should be accepted.');
}


function testResponseRowShape_() {
  const questionSet = {
    questionSetId: '11111111-1111-4111-8111-111111111111',
    roleTitle: 'Test role'
  };
  const answers = [{ question: { category: 'Intent', text: 'Question?', id: 'id' }, score: 3, notes: 'Note' }];
  const row = buildResponseRow_(new Date(), 'id', questionSet, 'Sample Candidate', answers, {
    rawTotal: 3,
    rawMax: 5,
    weightedPercent: 60
  });
  assertEqual_(row.length, RESPONSE_HEADERS.length, 'Response row/header length mismatch.');
}


function testConstantTimeEqual_() {
  assertEqual_(constantTimeEqual_('same', 'same'), true, 'Equal values must match.');
  assertEqual_(constantTimeEqual_('same', 'different'), false, 'Different values must not match.');
}


function assertEqual_(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`${message} Expected ${expected}, received ${actual}.`);
  }
}
