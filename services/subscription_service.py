from models import User, Subscription, db
from datetime import datetime
from flask_login import current_user

def check_feature_access(user_id, feature_type):
    """
    Centralized subscription-access system.
    Returns (has_access, message).
    """
    user = User.query.get(user_id)
    if not user:
        return False, "User not found."
        
    # Define what features need what minimum plan keywords
    # If the feature_type is one of these, we check if the user's plan features string contains it
    
    # 1. Check Active Paid Subscription
    active_sub = Subscription.query.filter_by(user_id=user_id, status='Active').order_by(Subscription.end_date.desc()).first()
    
    if active_sub:
        if active_sub.end_date < datetime.utcnow():
            active_sub.status = 'Expired'
            db.session.commit()
            active_sub = None
        else:
            plan_features = active_sub.plan.features.lower()
            
            # Map requested feature_type to required keywords in plan features
            if feature_type == 'AI Study Assistant' or feature_type.startswith('AI'):
                if 'ai' in plan_features or 'premium' in active_sub.plan.name.lower():
                    return True, ""
                return False, "This feature requires the Premium Plan."
                
            if feature_type in ['Assignments', 'Analytics', 'Discussions', 'Advanced Quizzes', 'Attendance']:
                if 'everything in basic' in plan_features or 'everything in standard' in plan_features or feature_type.lower() in plan_features:
                    return True, ""
                return False, "This feature requires the Standard or Premium Plan."
                
            # Basic features are allowed for all paid plans
            return True, ""
            
    # 2. Check Free Trial if no active paid subscription
    if user.trial_status == 'Trial Active' and user.trial_ends_at:
        if datetime.utcnow() > user.trial_ends_at:
            user.trial_status = 'Trial Expired'
            db.session.commit()
        else:
            # Trial active. Limit access.
            if feature_type in ['Course Access', 'Lessons', 'Study Materials', 'Basic Quizzes', 'Progress Tracking']:
                if feature_type == 'Basic Quizzes':
                    from models import Result
                    quiz_count = Result.query.filter(
                        Result.student_id == user_id,
                        Result.submitted_at >= user.trial_started_at
                    ).count()
                    if quiz_count >= 2:
                        return False, "Trial quiz limit reached. Subscribe to continue."
                return True, ""
            return False, f"{feature_type} is not available in the Free Trial. Please subscribe to a paid plan."
            
    return False, "This feature is available with a paid subscription. Please upgrade your plan to continue."
