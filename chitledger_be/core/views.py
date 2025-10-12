# Import Firebase to ensure it's initialized


from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from rest_framework.permissions import  IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Chit, ChitSchedule, Membership, Payment, User, ExternalMember
from .serializers import ChitCreateSerializer, ChitDetailSerializer, ChitListSerializer, ChitScheduleUpdateSerializer, PaymentCreateSerializer, PaymentSerializer, UserSignupSerializer, UserSigninSerializer, MembershipSerializer, ExternalMemberSerializer, ChitScheduleSerializer, ExternalMemberCreateSerializer
# import firebase
from firebase_admin import auth as firebase_auth

# ---------- Signup ----------
# Deprecated -- signup logic
# class SignupView(APIView):
#     def post(self, request):
#         serializer = UserSignupSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             return Response(
#                 {"message": "User registered successfully", "user_id": user.user_id},
#                 status=status.HTTP_201_CREATED,
#             )
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Signin ----------
class SigninView(APIView):
    def post(self, request):
        serializer = UserSigninSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            password = serializer.validated_data["password"]

            user = authenticate(request, phone_number=phone_number, password=password)
            if not user:
                return Response(
                    {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
                )

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.user_id,
                    "name": user.name,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PermissionRequiredView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            print(user)
            response_data = {"success": True}
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
class FirebaseSignupView(APIView):
    def post(self, request):
        try:
            print("🔥 Firebase signup endpoint called")
            
            id_token = request.data.get("idToken")
            fe_phone_number = request.data.get("phoneNumber")
            name = request.data.get("name")
            password = request.data.get("password")

            print(f"Received: phone={fe_phone_number}, name={name}, token_present={bool(id_token)}")

            if not id_token or not password or not name:
                return Response({
                    "error": "idToken, name, and password are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify Firebase token
            print("Verifying Firebase token...")
            decoded_token = firebase_auth.verify_id_token(id_token)
            phone_number = decoded_token.get("phone_number")
            
            print(f"✅ Token verified! Phone from token: {phone_number}")

            if not phone_number:
                return Response({
                    "error": "Phone number not found in token"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if user already exists
            if User.objects.filter(phone_number=phone_number).exists():
                return Response({
                    "error": "User with this phone number already exists"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create user
            serializer = UserSignupSerializer(data={
                "phone_number": phone_number,
                "name": name,
                "password": password,
            })

            if serializer.is_valid():
                user = serializer.save()
                print(f"✅ User created successfully: {user.phone_number}")
                return Response({
                    "message": "User registered successfully",
                    "user_id": str(user.user_id),
                    "phone_number": user.phone_number,
                    "name": user.name
                }, status=status.HTTP_201_CREATED)

            print(f"❌ Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except firebase_auth.InvalidIdTokenError as e:
            print(f"❌ Invalid Firebase token: {e}")
            return Response({
                "error": "Invalid Firebase ID token"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"❌ Signup error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Signup failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FirebasePasswordResetView(APIView):
    def post(self, request):
        try:
            id_token = request.data.get("idToken")
            phone_number = request.data.get("phoneNumber")
            new_password = request.data.get("newPassword")  # Expect "password" key, not "newPassword"

            if not id_token or not phone_number or not new_password:
                return Response({
                    "error": "idToken, phoneNumber, and password are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify Firebase ID token
            decoded_token = firebase_auth.verify_id_token(id_token)
            token_phone_number = decoded_token.get("phone_number")

            if token_phone_number != phone_number:
                return Response({
                    "error": "Phone number mismatch with token"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                return Response({
                    "error": "User not found"
                }, status=status.HTTP_404_NOT_FOUND)

            # Set the new password securely
            user.set_password(new_password)
            user.save()

            return Response({
                "message": "Password reset successful"
            }, status=status.HTTP_200_OK)

        except firebase_auth.InvalidIdTokenError:
            return Response({
                "error": "Invalid Firebase ID token"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"❌ Password reset error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Password reset failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================================================
# CHIT VIEWSET - Handles /api/chits/ endpoints
# ============================================================================
class ChitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Chit CRUD operations
    
    Endpoints:
    - GET    /api/chits/                     → List all chits
    - POST   /api/chits/                     → Create new chit
    - GET    /api/chits/{id}/                → Get chit details
    - PUT    /api/chits/{id}/                → Update chit
    - DELETE /api/chits/{id}/                → Delete chit
    - POST   /api/chits/{id}/add_external_member/  → Add member
    - GET    /api/chits/{id}/schedules/      → Get all schedules
    - GET    /api/chits/{id}/members/        → Get all members
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return chits where user is organizer"""
        user = self.request.user
        return Chit.objects.filter(organizer=user).distinct()
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return ChitCreateSerializer
        elif self.action == 'list':
            return ChitListSerializer
        return ChitDetailSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Create chit with external members and auto-generate schedules
        
        POST /api/chits/
        Body: {
            "title": "Diwali Chit",
            "total_slots": 20,
            "total_amount": "20000",
            "lift_amount": "1000",
            "start_date": "2025-11-01",
            "duration_months": 20,
            "external_members_data": [
                {"phone_number": "+91...", "name": "Rajesh", "slot_count": 1}
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chit = serializer.save()
        
        # Return detailed response
        response_serializer = ChitDetailSerializer(chit)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_external_member(self, request, pk=None):
        """
        Add external member to existing chit
        
        POST /api/chits/{id}/add_external_member/
        Body: {
            "phone_number": "+91...",
            "name": "New Member",
            "slot_count": 1
        }
        """
        chit = self.get_object()
        
        # Check if organizer
        if chit.organizer != request.user:
            return Response(
                {"error": "Only organizer can add members"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check available slots
        current_slots = (
            sum(m.slot_count for m in chit.memberships.all()) +
            sum(m.slot_count for m in chit.external_members.all())
        )
        requested_slots = request.data.get('slot_count', 1)
        
        if current_slots + requested_slots > chit.total_slots:
            return Response(
                {"error": "Not enough available slots"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExternalMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        external_member = ExternalMember.objects.create(
            chit=chit,
            **serializer.validated_data
        )
        
        response_serializer = ExternalMemberSerializer(external_member)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def schedules(self, request, pk=None):
        """
        Get all schedules for a chit
        
        GET /api/chits/{id}/schedules/
        """
        chit = self.get_object()
        schedules = chit.schedules.all().order_by('month_number')
        serializer = ChitScheduleSerializer(schedules, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        Get all members (verified + external) for a chit
        
        GET /api/chits/{id}/members/
        """
        chit = self.get_object()
        
        # Get verified members
        memberships = chit.memberships.all()
        verified_members = MembershipSerializer(memberships, many=True).data
        
        # Get external members
        external_members = chit.external_members.all()
        external_data = ExternalMemberSerializer(external_members, many=True).data
        
        return Response({
            'verified_members': verified_members,
            'external_members': external_data,
            'total_count': len(verified_members) + len(external_data)
        })
    

# ============================================================================
# CHIT ENDPOINTS
# ============================================================================

class ChitListCreateView(APIView):
    """
    GET  /api/chits/  - List all chits
    POST /api/chits/  - Create new chit
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List all chits for the organizer"""
        chits = Chit.objects.filter(organizer=request.user)
        serializer = ChitListSerializer(chits, many=True)
        return Response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create new chit with external members and auto-generate schedules"""
        serializer = ChitCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            chit = serializer.save()
            response_serializer = ChitDetailSerializer(chit)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChitDetailView(APIView):
    """
    GET    /api/chits/{id}/  - Get chit details
    PUT    /api/chits/{id}/  - Update chit
    DELETE /api/chits/{id}/  - Delete chit
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(Chit, pk=pk, organizer=user)
    
    def get(self, request, pk):
        """Get detailed chit information"""
        chit = self.get_object(pk, request.user)
        serializer = ChitDetailSerializer(chit)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update chit details"""
        chit = self.get_object(pk, request.user)
        serializer = ChitCreateSerializer(chit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = ChitDetailSerializer(chit)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete chit"""
        chit = self.get_object(pk, request.user)
        chit.delete()
        return Response({"message": "Chit deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class ChitAddExternalMemberView(APIView):
    """
    POST /api/chits/{id}/add-external-member/  - Add external member to chit
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        chit = get_object_or_404(Chit, pk=pk, organizer=request.user)
        
        # Check available slots
        current_slots = (
            sum(m.slot_count for m in chit.memberships.all()) +
            sum(m.slot_count for m in chit.external_members.all())
        )
        requested_slots = request.data.get('slot_count', 1)
        
        if current_slots + requested_slots > chit.total_slots:
            return Response(
                {"error": "Not enough available slots"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExternalMemberCreateSerializer(data=request.data)
        if serializer.is_valid():
            external_member = ExternalMember.objects.create(chit=chit, **serializer.validated_data)
            response_serializer = ExternalMemberSerializer(external_member)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChitSchedulesView(APIView):
    """
    GET /api/chits/{id}/schedules/  - Get all schedules for a chit
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        chit = get_object_or_404(Chit, pk=pk, organizer=request.user)
        schedules = chit.schedules.all().order_by('month_number')
        serializer = ChitScheduleSerializer(schedules, many=True)
        return Response(serializer.data)


class ChitMembersView(APIView):
    """
    GET /api/chits/{id}/members/  - Get all members (verified + external)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        chit = get_object_or_404(Chit, pk=pk, organizer=request.user)
        
        memberships = chit.memberships.all()
        verified_members = MembershipSerializer(memberships, many=True).data
        
        external_members = chit.external_members.all()
        external_data = ExternalMemberSerializer(external_members, many=True).data
        
        return Response({
            'verified_members': verified_members,
            'external_members': external_data,
            'total_count': len(verified_members) + len(external_data)
        })


# ============================================================================
# SCHEDULE ENDPOINTS
# ============================================================================

class ScheduleListView(APIView):
    """
    GET /api/schedules/  - List all schedules
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        schedules = ChitSchedule.objects.filter(chit__organizer=request.user)
        serializer = ChitScheduleSerializer(schedules, many=True)
        return Response(serializer.data)


class ScheduleDetailView(APIView):
    """
    GET /api/schedules/{id}/  - Get schedule details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        schedule = get_object_or_404(ChitSchedule, pk=pk, chit__organizer=request.user)
        serializer = ChitScheduleSerializer(schedule)
        return Response(serializer.data)


class ScheduleUpdateMonthView(APIView):
    """
    PATCH /api/schedules/{id}/update-month/  - Update monthly no_lift_amount
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        schedule = get_object_or_404(ChitSchedule, pk=pk, chit__organizer=request.user)
        
        serializer = ChitScheduleUpdateSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            response_serializer = ChitScheduleSerializer(schedule)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScheduleAssignLifterView(APIView):
    """
    POST /api/schedules/{id}/assign-lifter/  - Assign who lifted this month
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        schedule = get_object_or_404(ChitSchedule, pk=pk, chit__organizer=request.user)
        
        member_type = request.data.get('member_type')
        member_id = request.data.get('member_id')
        
        if member_type == 'verified':
            membership = get_object_or_404(Membership, membership_id=member_id, chit=schedule.chit)
            schedule.lifted_by_membership = membership
            schedule.lifted_by_external = None
        elif member_type == 'external':
            external_member = get_object_or_404(ExternalMember, member_id=member_id, chit=schedule.chit)
            schedule.lifted_by_external = external_member
            schedule.lifted_by_membership = None
        else:
            return Response(
                {"error": "Invalid member_type. Use 'verified' or 'external'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedule.save()
        serializer = ChitScheduleSerializer(schedule)
        return Response(serializer.data)


# ============================================================================
# PAYMENT ENDPOINTS
# ============================================================================

class PaymentListCreateView(APIView):
    """
    GET  /api/payments/  - List all payments
    POST /api/payments/  - Record new payment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        payments = Payment.objects.filter(
            chit_schedule__chit__organizer=request.user
        ).select_related('membership', 'external_member', 'chit_schedule')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save()
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentDetailView(APIView):
    """
    GET /api/payments/{id}/  - Get payment details
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        payment = get_object_or_404(
            Payment, 
            pk=pk, 
            chit_schedule__chit__organizer=request.user
        )
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)


class PaymentUpdateStatusView(APIView):
    """
    PATCH /api/payments/{id}/update-status/  - Update payment status
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        payment = get_object_or_404(
            Payment, 
            pk=pk, 
            chit_schedule__chit__organizer=request.user
        )
        
        new_status = request.data.get('status')
        if new_status not in ['paid', 'pending', 'late']:
            return Response(
                {"error": "Invalid status. Use 'paid', 'pending', or 'late'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = new_status
        payment.save()
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)


class PaymentByChitView(APIView):
    """
    GET /api/payments/by-chit/?chit_id=5  - Get all payments for a chit
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        chit_id = request.query_params.get('chit_id')
        if not chit_id:
            return Response(
                {"error": "chit_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = Payment.objects.filter(
            chit_schedule__chit_id=chit_id,
            chit_schedule__chit__organizer=request.user
        )
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class PaymentByMonthView(APIView):
    """
    GET /api/payments/by-month/?chit_id=5&month_number=3  - Get payments for specific month
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        chit_id = request.query_params.get('chit_id')
        month_number = request.query_params.get('month_number')
        
        if not chit_id or not month_number:
            return Response(
                {"error": "chit_id and month_number parameters required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payments = Payment.objects.filter(
            chit_schedule__chit_id=chit_id,
            month_number=month_number,
            chit_schedule__chit__organizer=request.user
        )
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


# ============================================================================
# EXTERNAL MEMBER ENDPOINTS
# ============================================================================

class ExternalMemberListView(APIView):
    """
    GET /api/external-members/  - List all external members
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        members = ExternalMember.objects.filter(chit__organizer=request.user)
        serializer = ExternalMemberSerializer(members, many=True)
        return Response(serializer.data)


class ExternalMemberDetailView(APIView):
    """
    GET    /api/external-members/{id}/  - Get member details
    PUT    /api/external-members/{id}/  - Update member
    DELETE /api/external-members/{id}/  - Remove member
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(ExternalMember, pk=pk, chit__organizer=user)
    
    def get(self, request, pk):
        member = self.get_object(pk, request.user)
        serializer = ExternalMemberSerializer(member)
        return Response(serializer.data)
    
    def put(self, request, pk):
        member = self.get_object(pk, request.user)
        serializer = ExternalMemberSerializer(member, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        member = self.get_object(pk, request.user)
        
        if member.payments.exists():
            return Response(
                {"error": "Cannot remove member with existing payments"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member.delete()
        return Response(
            {"message": "External member removed successfully"},
            status=status.HTTP_204_NO_CONTENT
        )