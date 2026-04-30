"""
Auto-Grading Service for Exams
Evaluates test attempts by comparing student answers against correct answers.
Supports: MCQ_SINGLE, MCQ_MULTI, NUMERICAL, TRUE_FALSE, FILL_BLANK
Subjective questions are flagged for manual review.
"""
import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Avg

logger = logging.getLogger(__name__)


def auto_grade_attempt(attempt):
    """
    Auto-grade a single test attempt.
    Returns dict with grading results.
    """
    from assessments.models import TestAttemptAnswer, Question

    answers = TestAttemptAnswer.objects.filter(attempt=attempt).select_related('question')

    total_questions = 0
    attempted = 0
    correct = 0
    incorrect = 0
    skipped = 0
    raw_score = Decimal('0')
    needs_manual_review = False

    for ans in answers:
        total_questions += 1
        q = ans.question

        if ans.status in ('SKIPPED', 'NOT_VISITED') or not ans.student_answer:
            skipped += 1
            ans.is_correct = None
            ans.marks_awarded = Decimal('0')
            ans.save(update_fields=['is_correct', 'marks_awarded'])
            continue

        attempted += 1

        # Determine correctness based on question type
        is_correct = _check_answer(q, ans)

        if is_correct is None:
            # Subjective or un-gradable — flag for manual review
            needs_manual_review = True
            ans.is_correct = None
            ans.marks_awarded = None
            ans.save(update_fields=['is_correct', 'marks_awarded'])
            continue

        ans.is_correct = is_correct

        if is_correct:
            correct += 1
            ans.marks_awarded = q.positive_marks or Decimal('4')
            raw_score += ans.marks_awarded
        else:
            incorrect += 1
            neg = q.negative_marks or Decimal('0')
            ans.marks_awarded = neg  # negative_marks is stored as negative value
            raw_score += neg

        ans.save(update_fields=['is_correct', 'marks_awarded'])

        # Update question stats
        q.total_attempts = (q.total_attempts or 0) + 1
        if is_correct:
            q.correct_attempts = (q.correct_attempts or 0) + 1
        if q.total_attempts > 0:
            q.success_rate = Decimal(str(round(q.correct_attempts / q.total_attempts * 100, 2)))
        q.save(update_fields=['total_attempts', 'correct_attempts', 'success_rate'])

    # Update attempt
    test_total_marks = attempt.test.total_marks or total_questions * 4
    percentage = (raw_score / test_total_marks * 100) if test_total_marks else Decimal('0')
    passing_marks = attempt.test.passing_marks or (test_total_marks * Decimal('0.33'))

    attempt.total_questions = total_questions
    attempt.attempted = attempted
    attempt.correct = correct
    attempt.incorrect = incorrect
    attempt.skipped = skipped
    attempt.raw_score = raw_score
    attempt.total_marks = test_total_marks
    attempt.percentage = max(percentage, Decimal('0'))

    if not needs_manual_review:
        attempt.result = 'PASS' if raw_score >= passing_marks else 'FAIL'
        attempt.status = 'EVALUATED'
    else:
        attempt.result = 'PENDING'
        attempt.status = 'SUBMITTED'  # Keep as submitted for manual review

    attempt.save(update_fields=[
        'total_questions', 'attempted', 'correct', 'incorrect', 'skipped',
        'raw_score', 'total_marks', 'percentage', 'result', 'status',
    ])

    # Calculate rank among all evaluated attempts for this test
    _update_ranks(attempt.test)

    return {
        'attempt_id': str(attempt.id),
        'total_questions': total_questions,
        'attempted': attempted,
        'correct': correct,
        'incorrect': incorrect,
        'skipped': skipped,
        'raw_score': float(raw_score),
        'percentage': float(percentage),
        'result': attempt.result,
        'status': attempt.status,
        'needs_manual_review': needs_manual_review,
    }


def _check_answer(question, answer):
    """
    Compare student answer against correct answer.
    Returns True (correct), False (incorrect), or None (needs manual review).
    """
    q_type = question.question_type
    student_ans = (answer.student_answer or '').strip().upper()
    correct_ans = (question.correct_answer or '').strip().upper()

    if not correct_ans:
        return None

    if q_type == 'MCQ_SINGLE':
        return student_ans == correct_ans

    elif q_type == 'TRUE_FALSE':
        # Normalize TRUE/FALSE, T/F, 1/0
        true_vals = {'TRUE', 'T', '1', 'YES'}
        false_vals = {'FALSE', 'F', '0', 'NO'}
        student_bool = student_ans in true_vals
        correct_bool = correct_ans in true_vals
        if student_ans in true_vals or student_ans in false_vals:
            return student_bool == correct_bool
        return student_ans == correct_ans

    elif q_type == 'MCQ_MULTI':
        # Multi-select: compare sorted sets of selected options
        student_set = set(s.strip() for s in student_ans.replace(',', ' ').split() if s.strip())
        correct_set = set(s.strip() for s in correct_ans.replace(',', ' ').split() if s.strip())
        return student_set == correct_set

    elif q_type == 'NUMERICAL':
        try:
            student_val = Decimal(answer.student_answer_value or answer.student_answer or '0')
            correct_val = question.correct_answer_value or Decimal(question.correct_answer or '0')
            tolerance = question.numerical_tolerance or Decimal('0')
            return abs(student_val - correct_val) <= abs(tolerance)
        except Exception:
            return False

    elif q_type == 'FILL_BLANK':
        # Case-insensitive exact match (with trimming)
        return student_ans == correct_ans

    elif q_type in ('SUBJECTIVE', 'COMPREHENSION'):
        return None  # Needs manual review

    elif q_type == 'ASSERTION_REASON':
        return student_ans == correct_ans

    elif q_type == 'MATRIX_MATCH':
        return student_ans == correct_ans

    else:
        return student_ans == correct_ans


def _update_ranks(test):
    """Update rank and percentile for all evaluated attempts of a test."""
    from assessments.models import TestAttempt

    attempts = TestAttempt.objects.filter(
        test=test, status='EVALUATED'
    ).order_by('-raw_score', 'time_taken_seconds')

    total = attempts.count()
    for rank, attempt in enumerate(attempts, 1):
        attempt.rank = rank
        if total > 1:
            attempt.percentile = Decimal(str(round((total - rank) / (total - 1) * 100, 2)))
        else:
            attempt.percentile = Decimal('100')
        attempt.save(update_fields=['rank', 'percentile'])


def auto_grade_test(test):
    """
    Auto-grade ALL submitted (ungraded) attempts for a test.
    Returns list of results.
    """
    from assessments.models import TestAttempt

    pending_attempts = TestAttempt.objects.filter(
        test=test,
        status__in=['SUBMITTED', 'AUTO_SUBMITTED']
    )

    results = []
    for attempt in pending_attempts:
        try:
            result = auto_grade_attempt(attempt)
            results.append(result)
            logger.info(f"Auto-graded attempt {attempt.id}: {result['result']} ({result['percentage']}%)")
        except Exception as e:
            logger.error(f"Error grading attempt {attempt.id}: {e}")
            results.append({
                'attempt_id': str(attempt.id),
                'error': str(e),
            })

    return results


def generate_test_report(test):
    """
    Generate comprehensive test analytics report.
    """
    from assessments.models import TestAttempt, TestAttemptAnswer, Question

    attempts = TestAttempt.objects.filter(test=test, status='EVALUATED')
    total_attempts = attempts.count()

    if total_attempts == 0:
        return {'message': 'No evaluated attempts found'}

    stats = attempts.aggregate(
        avg_score=Avg('raw_score'),
        avg_percentage=Avg('percentage'),
        avg_time=Avg('time_taken_seconds'),
    )

    pass_count = attempts.filter(result='PASS').count()
    fail_count = attempts.filter(result='FAIL').count()

    # Question-wise analysis
    questions = Question.objects.filter(test=test, is_active=True).order_by('question_order')
    question_analysis = []
    for q in questions:
        q_answers = TestAttemptAnswer.objects.filter(question=q, attempt__in=attempts)
        q_total = q_answers.count()
        q_correct = q_answers.filter(is_correct=True).count()
        q_incorrect = q_answers.filter(is_correct=False).count()
        q_skipped = q_answers.filter(is_correct__isnull=True).count()

        question_analysis.append({
            'question_order': q.question_order,
            'question_text': q.question_text[:100],
            'question_type': q.question_type,
            'difficulty': q.difficulty,
            'total_responses': q_total,
            'correct': q_correct,
            'incorrect': q_incorrect,
            'skipped': q_skipped,
            'accuracy': round(q_correct / q_total * 100, 1) if q_total else 0,
        })

    return {
        'test_id': str(test.id),
        'test_title': test.title,
        'total_attempts': total_attempts,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'pass_rate': round(pass_count / total_attempts * 100, 1) if total_attempts else 0,
        'avg_score': float(stats['avg_score'] or 0),
        'avg_percentage': float(stats['avg_percentage'] or 0),
        'avg_time_seconds': int(stats['avg_time'] or 0),
        'question_analysis': question_analysis,
    }
