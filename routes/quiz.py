from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Quiz, Question, Answer, Result
from models import Course
from models import db
from datetime import datetime

quiz_bp = Blueprint('quiz', __name__, url_prefix='/quiz')

@quiz_bp.route('/course/<int:course_id>')
@login_required
def list_quizzes(course_id):
    """
    Handles the list quizzes functionality.
    """
    course = Course.query.get_or_404(course_id)
    quizzes = Quiz.query.filter_by(course_id=course.id).all()
    # Check if user already took the quiz
    user_results = {res.quiz_id: res for res in Result.query.filter_by(student_id=current_user.id).all()}
    return render_template('quizzes/quiz_list.html', course=course, quizzes=quizzes, user_results=user_results)

@quiz_bp.route('/take/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    """
    Handles the take quiz functionality.
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if already taken
    existing_result = Result.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).first()
    if existing_result:
        flash(f'You have already taken this quiz. Your score: {existing_result.score}/{existing_result.total}', 'info')
        return redirect(url_for('quiz.list_quizzes', course_id=quiz.course_id))
        
    if request.method == 'POST':
        score = 0
        total = len(quiz.questions)
        
        for question in quiz.questions:
            # We get the answer ID selected by the user
            selected_answer_id = request.form.get(f'question_{question.id}')
            if selected_answer_id:
                answer = Answer.query.get(int(selected_answer_id))
                if answer and answer.is_correct and answer.question_id == question.id:
                    score += 1
                    
        # Save Result to DB (Automated Grading)
        new_result = Result(
            quiz_id=quiz.id,
            student_id=current_user.id,
            score=score,
            total=total,
            submitted_at=datetime.utcnow()
        )
        db.session.add(new_result)
        db.session.commit()
        
        flash(f'Quiz submitted! You scored {score} out of {total}!', 'success')
        return redirect(url_for('quiz.quiz_result', quiz_id=quiz.id))
        
    return render_template('quizzes/take_quiz.html', quiz=quiz)

@quiz_bp.route('/result/<int:quiz_id>')
@login_required
def quiz_result(quiz_id):
    """
    Handles the quiz result functionality.
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    result = Result.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).first()
    
    if not result:
        flash('You have not taken this quiz yet.', 'warning')
        return redirect(url_for('quiz.list_quizzes', course_id=quiz.course_id))
        
    return render_template('quizzes/quiz_result.html', quiz=quiz, result=result)

