from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Quiz, Question
from models import Course
from models import db

quiz_bp = Blueprint('quiz', __name__, url_prefix='/quiz')

@quiz_bp.route('/course/<int:course_id>')
@login_required
def list_quizzes(course_id):
    course = Course.query.get_or_404(course_id)
    quizzes = Quiz.query.filter_by(course_id=course.id).all()
    return render_template('quizzes/quiz_list.html', course=course, quizzes=quizzes)

@quiz_bp.route('/take/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        score = 0
        total = len(quiz.questions)
        for question in quiz.questions:
            answer = request.form.get(f'question_{question.id}')
            if answer == question.correct_option:
                score += 1
                
        flash(f'You scored {score} out of {total}!', 'info')
        return redirect(url_for('quiz.list_quizzes', course_id=quiz.course_id))
        
    return render_template('quizzes/take_quiz.html', quiz=quiz)
