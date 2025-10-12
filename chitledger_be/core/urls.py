from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import ChitAddExternalMemberView, ChitDetailView, ChitListCreateView, ChitMembersView, ChitSchedulesView, ChitViewSet, ExternalMemberDetailView, ExternalMemberListView, PaymentByChitView, PaymentByMonthView, PaymentDetailView, PaymentListCreateView, PaymentUpdateStatusView, ScheduleAssignLifterView, ScheduleDetailView, ScheduleListView, ScheduleUpdateMonthView, SigninView,FirebasePasswordResetView, PermissionRequiredView, FirebaseSignupView


# router = DefaultRouter()
# router.register(r'chits', ChitViewSet, basename='chit')


urlpatterns = [
    # path('', include(router.urls)),
    path("signup/", FirebaseSignupView.as_view(), name="signup"),
    path("signin/", SigninView.as_view(), name="signin"),
    path("forgotpassword/", FirebasePasswordResetView.as_view(), name="forgot-password"),
    path("authcheck/", PermissionRequiredView.as_view(), name="authcheck"),
    # ============================================================================
    # CHIT MANAGEMENT ENDPOINTS
    # ============================================================================
    path('chits/', ChitListCreateView.as_view(), name='chit-list-create'),
    # GET  /api/chits/  - List all chits for organizer
    # POST /api/chits/  - Create new chit with external members
    
    path('chits/<int:pk>/', ChitDetailView.as_view(), name='chit-detail'),
    # GET    /api/chits/{id}/  - Get chit details
    # PUT    /api/chits/{id}/  - Update chit
    # DELETE /api/chits/{id}/  - Delete chit
    
    path('chits/<int:pk>/add-external-member/', ChitAddExternalMemberView.as_view(), name='chit-add-member'),
    # POST /api/chits/{id}/add-external-member/  - Add external member to chit
    
    path('chits/<int:pk>/schedules/', ChitSchedulesView.as_view(), name='chit-schedules'),
    # GET /api/chits/{id}/schedules/  - Get all monthly schedules for chit
    
    path('chits/<int:pk>/members/', ChitMembersView.as_view(), name='chit-members'),
    # GET /api/chits/{id}/members/  - Get all members (verified + external)
    
    # ============================================================================
    # SCHEDULE MANAGEMENT ENDPOINTS
    # ============================================================================
    path('schedules/', ScheduleListView.as_view(), name='schedule-list'),
    # GET /api/schedules/  - List all schedules for organizer's chits
    
    path('schedules/<int:pk>/', ScheduleDetailView.as_view(), name='schedule-detail'),
    # GET /api/schedules/{id}/  - Get schedule details
    
    path('schedules/<int:pk>/update-month/', ScheduleUpdateMonthView.as_view(), name='schedule-update-month'),
    # PATCH /api/schedules/{id}/update-month/  - Update no_lift_amount for month
    
    path('schedules/<int:pk>/assign-lifter/', ScheduleAssignLifterView.as_view(), name='schedule-assign-lifter'),
    # POST /api/schedules/{id}/assign-lifter/  - Assign who lifted this month
    
    # ============================================================================
    # PAYMENT MANAGEMENT ENDPOINTS
    # ============================================================================
    path('payments/', PaymentListCreateView.as_view(), name='payment-list-create'),
    # GET  /api/payments/  - List all payments
    # POST /api/payments/  - Record new payment
    
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    # GET /api/payments/{id}/  - Get payment details
    
    path('payments/<int:pk>/update-status/', PaymentUpdateStatusView.as_view(), name='payment-update-status'),
    # PATCH /api/payments/{id}/update-status/  - Update payment status (paid/pending/late)
    
    path('payments/by-chit/', PaymentByChitView.as_view(), name='payment-by-chit'),
    # GET /api/payments/by-chit/?chit_id=5  - Get all payments for a specific chit
    
    path('payments/by-month/', PaymentByMonthView.as_view(), name='payment-by-month'),
    # GET /api/payments/by-month/?chit_id=5&month_number=3  - Get payments for specific month
    
    # ============================================================================
    # EXTERNAL MEMBER MANAGEMENT ENDPOINTS
    # ============================================================================
    path('external-members/', ExternalMemberListView.as_view(), name='external-member-list'),
    # GET /api/external-members/  - List all external members
    
    path('external-members/<int:pk>/', ExternalMemberDetailView.as_view(), name='external-member-detail'),
    # GET    /api/external-members/{id}/  - Get member details
    # PUT    /api/external-members/{id}/  - Update member
    # DELETE /api/external-members/{id}/  - Remove member
    
    # ============================================================================
    # DASHBOARD & ANALYTICS ENDPOINTS
    # ============================================================================
    # path('dashboard/organizer/', OrganizerDashboardView.as_view(), name='organizer-dashboard'),
    # # GET /api/dashboard/organizer/  - Get overview of all chits for organizer
    
    # path('dashboard/chit/<int:chit_id>/', ChitDashboardView.as_view(), name='chit-dashboard'),
    # # GET /api/dashboard/chit/{id}/  - Get comprehensive chit dashboard
    
    # path('dashboard/chit/<int:chit_id>/current-month/', CurrentMonthView.as_view(), name='current-month'),
    # # GET /api/dashboard/chit/{id}/current-month/  - Get current month details
    
    # path('dashboard/chit/<int:chit_id>/member-history/', MemberPaymentHistoryView.as_view(), name='member-history'),
    # # GET /api/dashboard/chit/{id}/member-history/?member_id=1&member_type=external
    
    # path('dashboard/chit/<int:chit_id>/check-eligibility/', CheckLiftEligibilityView.as_view(), name='check-eligibility'),
    # # GET /api/dashboard/chit/{id}/check-eligibility/?member_id=1&member_type=external
    
    # path('dashboard/chit/<int:chit_id>/validate/', ChitValidationView.as_view(), name='chit-validation'),
    # # GET /api/dashboard/chit/{id}/validate/  - Validate chit completion status
    
    # path('dashboard/chit/<int:chit_id>/monthly-report/', MonthlyReportView.as_view(), name='monthly-report'),
    # # GET /api/dashboard/chit/{id}/monthly-report/  - Get detailed monthly report
    
    # path('dashboard/chit/<int:chit_id>/payment-reminders/', PaymentReminderView.as_view(), name='payment-reminders'),
    # # GET /api/dashboard/chit/{id}/payment-reminders/  - Get pending payment reminders
    
    # path('dashboard/chit/<int:chit_id>/bulk-payment-update/', BulkPaymentUpdateView.as_view(), name='bulk-payment-update'),
    # POST /api/dashboard/chit/{id}/bulk-payment-update/  - Bulk update payment statuses
     # JWT built-in endpoints
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),   # login (access + refresh)
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # get new access token
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),     # optional, verify token validity
]
