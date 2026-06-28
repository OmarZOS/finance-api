

class SubscriptionRepository:
    """Repository for subscription operations"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        """Get plan by ID"""
        try:
            return self.session.query(Plan).filter(
                Plan.id_plan == plan_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to get plan {plan_id}: {e}")
            return None
    
    def get_all_plans(self, plan_type: Optional[str] = None) -> List[Plan]:
        """Get all plans, optionally filtered by type"""
        try:
            query = self.session.query(Plan)
            if plan_type:
                query = query.filter(Plan.plan_type == plan_type)
            return query.order_by(Plan.plan_price).all()
        except Exception as e:
            logger.error(f"Failed to get plans: {e}")
            return []
    
    def get_user_subscription(self, user_id: int) -> Optional[Plan]:
        """Get user's current subscription plan"""
        try:
            user = self.session.query(AppUser).filter(
                AppUser.id_app_user == user_id
            ).first()
            
            if not user or not user.app_user_subscription_ref:
                return None
            
            return self.get_plan_by_id(user.app_user_subscription_ref)
        except Exception as e:
            logger.error(f"Failed to get user subscription: {e}")
            return None
    
    def update_user_subscription(self, user_id: int, plan_id: int) -> Optional[AppUser]:
        """Update user's subscription plan"""
        try:
            user = self.session.query(AppUser).filter(
                AppUser.id_app_user == user_id
            ).first()
            
            if not user:
                return None
            
            plan = self.get_plan_by_id(plan_id)
            if not plan:
                return None
            
            user.app_user_subscription_ref = plan_id
            user.app_user_last_updated = datetime.now()
            
            self.session.flush()
            return user
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update user subscription: {e}")
            return None
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        try:
            total_users = self.session.query(AppUser).count()
            subscribed_users = self.session.query(AppUser).filter(
                AppUser.app_user_subscription_ref.isnot(None)
            ).count()
            
            # Get plan distribution
            plan_distribution = self.session.query(
                Plan.plan_name,
                func.count(AppUser.id_app_user).label('count')
            ).join(AppUser, AppUser.app_user_subscription_ref == Plan.id_plan).group_by(
                Plan.id_plan
            ).all()
            
            return {
                'total_users': total_users,
                'subscribed_users': subscribed_users,
                'subscription_rate': (subscribed_users / total_users * 100) if total_users > 0 else 0,
                'plan_distribution': [
                    {'plan': p[0], 'count': p[1]} for p in plan_distribution
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get subscription stats: {e}")
            return {}
