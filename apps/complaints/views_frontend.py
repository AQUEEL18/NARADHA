"""
Frontend views for Complaint app (Django templates).
"""
import datetime
import decimal
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import File
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.views.generic import TemplateView, CreateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import (
    Complaint, ComplaintCategory, ComplaintProof, ComplaintHistory,
    ComplaintEndorsement, ComplaintStatus,
)
from .forms import ComplaintForm, ComplaintStep1Form, ComplaintStep2Form, ComplaintStep3Form

# Map MIME top-level types onto ComplaintProof.proof_type choices
PROOF_TYPE_MAP = {
    'IMAGE': 'PHOTO',
    'VIDEO': 'VIDEO',
    'AUDIO': 'AUDIO',
    'APPLICATION': 'DOCUMENT',
    'TEXT': 'DOCUMENT',
}


def _staged_root():
    """Base directory for step-2 uploads staged between wizard steps."""
    return Path(settings.MEDIA_ROOT) / 'staged_uploads'


def _purge_stale_staged_uploads(max_age_hours=24):
    """Best-effort removal of staged uploads abandoned by users."""
    root = _staged_root()
    if not root.exists():
        return
    cutoff = time.time() - max_age_hours * 3600
    for child in root.iterdir():
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            pass


def _clear_staged(session_data):
    """Delete any files staged by a previous step-2 submission."""
    if not session_data:
        return
    for item in session_data.get('_staged_proofs', []):
        shutil.rmtree(os.path.dirname(item['path']), ignore_errors=True)
    session_data.pop('_staged_proofs', None)


def _run_ai_pipeline(complaint):
    """Dispatch the AI chain for a freshly submitted complaint.

    verify evidence -> score priority (-> SLA deadline) . Routing is
    dispatched separately once a human reviewer approves the complaint
    (Phase 3: human-in-the-loop before an official is assigned).
    Runs synchronously in dev (CELERY_TASK_ALWAYS_EAGER=True).
    """
    from apps.ai_services.tasks import (
        verify_complaint_proofs, score_complaint_priority,
    )
    for task in (verify_complaint_proofs, score_complaint_priority):
        try:
            task.delay(complaint.id)
        except Exception:
            # Broker/worker unavailable: complaint stays SUBMITTED and the
            # Celery beat schedule or a worker can pick it up later.
            break


def _json_safe(value):
    """Convert form values into JSON-serializable types for session storage."""
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if hasattr(value, 'pk'):  # model instances (e.g. ModelChoiceField values)
        return value.pk
    return value


class HomeView(TemplateView):
    """Home page view."""
    template_name = 'complaints/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        total_complaints = Complaint.objects.filter(is_deleted=False).count()
        resolved_complaints = Complaint.objects.filter(status='RESOLVED').count()
        pending_complaints = Complaint.objects.exclude(status__in=['RESOLVED', 'REJECTED']).count()
        
        # Get recent complaints with published commitments (public trust feed)
        recent_complaints = Complaint.objects.filter(
            commitment_visible=True,
            commitment_date__isnull=False,
            is_deleted=False,
        ).exclude(status='REJECTED').select_related(
            'category', 'assigned_official', 'assigned_department'
        ).order_by('-commitment_date')[:6]
        
        context.update({
            'total_complaints': total_complaints,
            'resolved_complaints': resolved_complaints,
            'pending_complaints': pending_complaints,
            'recent_complaints': recent_complaints,
        })
        
        return context


class ComplaintCreateView(LoginRequiredMixin, TemplateView):
    """Multi-step complaint creation view."""
    template_name = 'complaints/complaint_create.html'
    form_classes = {
        'step1': ComplaintStep1Form,
        'step2': ComplaintStep2Form,
        'step3': ComplaintStep3Form,
    }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get categories
        categories = ComplaintCategory.objects.filter(is_active=True)
        
        # Get current step
        step = self.request.GET.get('step', '1')
        
        # Get form for current step
        form_class = self.form_classes.get(f'step{step}', ComplaintStep1Form)
        
        # Initialize form
        if self.request.method == 'GET':
            form = form_class()
        else:
            form = form_class(self.request.POST, self.request.FILES)
        
        context.update({
            'categories': categories,
            'step': step,
            'form': form,
            'form_classes': self.form_classes,
        })
        
        # Phase 12 - duplicate prevention: before the final submit, surface
        # open complaints in the same category near the entered location so
        # the citizen can endorse instead of duplicate-filing.
        if step == '3':
            context['similar_complaints'] = self._find_similar_complaints()
        
        return context
    
    def _find_similar_complaints(self):
        """Proximity + category match against existing open complaints."""
        data = self.request.session.get('complaint_data') or {}
        category_id = data.get('category')
        location = data.get('location_address') or ''
        if not category_id or not location:
            return Complaint.objects.none()
        
        query = Q()
        tokens = [t for t in re.split(r'\W+', location.lower()) if len(t) > 3][:6]
        for token in tokens:
            query |= Q(location_address__icontains=token)
        
        try:
            lat = decimal.Decimal(str(data.get('latitude')))
            lon = decimal.Decimal(str(data.get('longitude')))
            query |= (
                Q(latitude__gte=lat - decimal.Decimal('0.01'),
                  latitude__lte=lat + decimal.Decimal('0.01')) &
                Q(longitude__gte=lon - decimal.Decimal('0.01'),
                  longitude__lte=lon + decimal.Decimal('0.01'))
            )
        except (decimal.InvalidOperation, TypeError):
            pass
        
        similar = Complaint.objects.filter(
            Q(category_id=category_id) & query,
            is_deleted=False,
        ).exclude(
            status__in=[ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED]
        ).select_related('category', 'assigned_department')
        if self.request.user.is_authenticated:
            similar = similar.exclude(citizen=self.request.user)
        return similar.distinct()[:5]
    
    def post(self, request, *args, **kwargs):
        step = request.POST.get('step', '1')
        form_class = self.form_classes.get(f'step{step}', ComplaintStep1Form)
        form = form_class(request.POST, request.FILES)
        
        if form.is_valid() and step == '2':
            # Files posted at step 2 cannot survive the redirect to step 3,
            # so stage them on disk now and attach them when the complaint
            # is finally created at step 3.
            staging_error = self._stage_proofs(request, request.FILES.getlist('proofs'))
            if staging_error:
                form.add_error('proofs', staging_error)
        
        if form.is_valid():
            # Store form data in session
            if 'complaint_data' not in request.session:
                request.session['complaint_data'] = {}
            
            request.session['complaint_data'].update(
                {
                    key: _json_safe(value)
                    for key, value in form.cleaned_data.items()
                    if key != 'proofs'
                }
            )
            request.session.modified = True
            
            # If this is the last step, create the complaint
            if step == '3':
                complaint_data = request.session.get('complaint_data', {})
                
                # Create complaint
                complaint = Complaint.objects.create(
                    citizen=request.user,
                    title=complaint_data.get('title', ''),
                    description=complaint_data.get('description', ''),
                    location_address=complaint_data.get('location_address', ''),
                    latitude=complaint_data.get('latitude'),
                    longitude=complaint_data.get('longitude'),
                    category_id=complaint_data.get('category'),
                    jurisdiction_id=complaint_data.get('jurisdiction'),
                    status='SUBMITTED',
                    submitted_at=timezone.now(),
                    source='WEB'
                )
                
                # Attach the evidence staged at step 2
                attached_count = self._attach_staged_proofs(complaint, complaint_data)
                
                # Immutable audit trail: the submission itself (Phase 8)
                complaint.record_status_change(
                    ComplaintStatus.SUBMITTED,
                    changed_by=request.user,
                    notes=(f'Complaint submitted via web portal with '
                           f'{attached_count} evidence file(s)'),
                )
                
                # Phase 2 + 4: AI evidence verification & priority scoring.
                # (Routing waits for human review approval - Phase 3.)
                _run_ai_pipeline(complaint)
                
                # Clear session data
                del request.session['complaint_data']
                
                return redirect('complaint_detail', complaint_id=complaint.complaint_id)
            else:
                # Go to next step
                next_step = int(step) + 1
                return redirect(f'/file-complaint/?step={next_step}')
        
        return self.render_to_response(self.get_context_data(form=form))
    
    def _stage_proofs(self, request, files):
        """Persist step-2 uploads to a private temp dir until step 3.

        Returns an error string for the form when a file violates the
        configured size limit, otherwise None.
        """
        _purge_stale_staged_uploads()
        session_data = request.session.get('complaint_data') or {}
        # The user may have gone "Back" and re-uploaded; drop the old batch
        _clear_staged(session_data)
        request.session['complaint_data'] = session_data
        
        max_mb = settings.NARADHA['MAX_PROOF_SIZE_MB']
        max_bytes = max_mb * 1024 * 1024
        oversized = [f.name for f in files if f.size > max_bytes]
        if oversized:
            return (
                f'Files exceed the {max_mb} MB per-file limit: '
                + ', '.join(oversized)
            )
        
        if not files:
            session_data.pop('_staged_proofs', None)
            request.session.modified = True
            return None
        
        staged_dir = _staged_root() / uuid.uuid4().hex
        staged_dir.mkdir(parents=True, exist_ok=True)
        staged = []
        for index, f in enumerate(files):
            filename = f'{index:03d}_{get_valid_filename(f.name or "upload.bin")}'
            dest = staged_dir / filename
            with open(dest, 'wb') as out:
                for chunk in f.chunks():
                    out.write(chunk)
            staged.append({
                'path': str(dest),
                'name': f.name,
                'content_type': f.content_type or '',
                'size': f.size,
            })
        
        session_data['_staged_proofs'] = staged
        request.session.modified = True
        return None
    
    def _attach_staged_proofs(self, complaint, complaint_data):
        """Move files staged at step 2 into ComplaintProof records."""
        used_dirs = set()
        attached = 0
        for item in complaint_data.get('_staged_proofs', []):
            path = item['path']
            if not os.path.exists(path):
                continue
            top_level = (item['content_type'] or 'application').split('/')[0].upper()
            with open(path, 'rb') as fh:
                proof = ComplaintProof(
                    complaint=complaint,
                    proof_type=PROOF_TYPE_MAP.get(top_level, 'DOCUMENT'),
                    file_size=item['size'],
                    file_type=item['content_type'],
                )
                proof.file.save(item['name'], File(fh), save=False)
                proof.save()
            used_dirs.add(os.path.dirname(path))
            attached += 1
        # Remove temp dirs only after all files in them have been consumed
        for directory in used_dirs:
            shutil.rmtree(directory, ignore_errors=True)
        complaint_data.pop('_staged_proofs', None)
        return attached


class ComplaintListView(LoginRequiredMixin, ListView):
    """List complaints view."""
    model = Complaint
    template_name = 'complaints/complaint_list.html'
    context_object_name = 'complaints'
    paginate_by = 10
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin or user.is_superuser:
            return Complaint.objects.filter(is_deleted=False).order_by('-created_at')
        elif user.is_reviewer():
            # Phase 3: human review queue - complaints that passed AI
            # verification and wait for a reviewer decision, sorted so the
            # highest-confidence (fast lane) items come first.
            return Complaint.objects.filter(
                is_deleted=False,
                status__in=[
                    ComplaintStatus.PROOF_RECEIVED,
                    ComplaintStatus.AWAITING_HUMAN_REVIEW,
                ],
            ).order_by('-ai_confidence_score', '-created_at')
        elif user.is_official():
            return Complaint.objects.filter(
                Q(assigned_official=user) | 
                Q(assigned_department=user.department) |
                Q(jurisdiction=user.jurisdiction)
            ).order_by('-created_at')
        elif user.is_field_worker():
            return Complaint.objects.filter(assigned_field_worker=user).order_by('-created_at')
        else:
            # Citizens: their own complaints, plus every open complaint
            # (anonymized) so the community can endorse similar issues
            # instead of duplicate-filing (Phase 12). Drafts stay private;
            # other people's rejections stay hidden.
            return Complaint.objects.filter(
                Q(citizen=user)
                | Q(commitment_visible=True)
                | ~Q(status__in=[ComplaintStatus.DRAFT, ComplaintStatus.REJECTED])
            ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['review_queue'] = user.is_authenticated and user.is_reviewer()
        return context


class ComplaintDetailView(DetailView):
    """Complaint detail view."""
    model = Complaint
    template_name = 'complaints/complaint_detail.html'
    context_object_name = 'complaint'
    pk_url_kwarg = 'complaint_id'
    slug_url_kwarg = 'complaint_id'

    def get_object(self, queryset=None):
        """Look up complaints by their string complaint_id (not pk)."""
        return get_object_or_404(
            self.get_queryset(), complaint_id=self.kwargs['complaint_id']
    )
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_authenticated:
            if user.is_admin or user.is_superuser:
                return Complaint.objects.filter(is_deleted=False)
            elif user.is_official():
                return Complaint.objects.filter(
                    Q(assigned_official=user) | 
                    Q(assigned_department=user.department) |
                    Q(jurisdiction=user.jurisdiction) |
                    Q(commitment_visible=True)
                )
            elif user.is_field_worker():
                return Complaint.objects.filter(
                    Q(assigned_field_worker=user) | 
                    Q(commitment_visible=True)
                )
            else:
                # Citizens: own complaints + public commitments + open
                # complaints (anonymized) so they can endorse similar issues.
                return Complaint.objects.filter(
                    Q(citizen=user)
                    | Q(commitment_visible=True)
                    | ~Q(status__in=[ComplaintStatus.DRAFT, ComplaintStatus.REJECTED])
                )
        else:
            return Complaint.objects.filter(commitment_visible=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        complaint = self.object
        
        # Get related data
        proofs = complaint.proofs.all()
        history = complaint.history.all()
        endorsements = complaint.endorsements.all()
        
        # Check if user can edit
        user = self.request.user
        can_edit = False
        can_verify = False
        can_assign = False
        can_commit = False
        can_rate = False
        
        if user.is_authenticated:
            if user.is_admin or user.is_superuser:
                can_edit = can_verify = can_assign = can_commit = True
            elif user.is_official():
                can_edit = complaint.assigned_official == user
                can_assign = True
                can_commit = complaint.assigned_official == user
            elif user.is_reviewer():
                can_verify = True
            elif user.is_citizen() and complaint.citizen == user:
                can_edit = True
                can_rate = complaint.status == 'AWAITING_CITIZEN_VERIFICATION'
        
        # Phase 12: endorsement availability (citizens, not the filer, on
        # complaints that are still open)
        has_endorsed = False
        can_endorse = False
        if user.is_authenticated and user.is_citizen():
            if complaint.citizen_id != user.id and complaint.status not in (
                ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED
            ):
                can_endorse = True
                has_endorsed = ComplaintEndorsement.objects.filter(
                    complaint=complaint, citizen=user
                ).exists()
        
        # Field worker picker for officials releasing a complaint to execution
        field_workers = []
        if can_commit:
            from apps.users.models import CustomUser
            field_workers = list(
                CustomUser.objects.filter(role='FIELD_WORKER', is_active=True)
            )
        
        context.update({
            'proofs': proofs,
            'history': history,
            'endorsements': endorsements,
            'can_edit': can_edit,
            'can_verify': can_verify,
            'can_assign': can_assign,
            'can_commit': can_commit,
            'can_rate': can_rate,
            'can_endorse': can_endorse,
            'has_endorsed': has_endorsed,
            'field_workers': field_workers,
            'ai_threshold': settings.NARADHA['AI_CONFIDENCE_THRESHOLD'],
        })
        
        return context


class ComplaintTrackingView(LoginRequiredMixin, DetailView):
    """Complaint tracking view for citizens."""
    model = Complaint
    template_name = 'complaints/complaint_track.html'
    context_object_name = 'complaint'
    pk_url_kwarg = 'complaint_id'

    def get_object(self, queryset=None):
        """Look up complaints by their string complaint_id (not pk)."""
        return get_object_or_404(
            Complaint, complaint_id=self.kwargs['complaint_id'], citizen=self.request.user
        )
    
    def get_queryset(self):
        user = self.request.user
        return Complaint.objects.filter(citizen=user)


class ComplaintVerifyView(LoginRequiredMixin, DetailView):
    """Complaint verification view for field workers."""
    model = Complaint
    template_name = 'complaints/complaint_verify.html'
    context_object_name = 'complaint'
    pk_url_kwarg = 'complaint_id'

    def get_object(self, queryset=None):
        """Look up complaints by their string complaint_id (not pk)."""
        return get_object_or_404(
            Complaint,
            complaint_id=self.kwargs['complaint_id'],
            assigned_field_worker=self.request.user
        )
    
    def get_queryset(self):
        user = self.request.user
        return Complaint.objects.filter(assigned_field_worker=user)


# ---------------------------------------------------------------------------
# Workflow actions (Phase 3 / 7 / 10 / 11 / 12) - one POST dispatcher gated
# per role. Every successful action writes an immutable history entry.
# ---------------------------------------------------------------------------
OPEN_STATUSES = [
    ComplaintStatus.SUBMITTED, ComplaintStatus.PROOF_RECEIVED,
    ComplaintStatus.AWAITING_HUMAN_REVIEW, ComplaintStatus.VERIFIED,
    ComplaintStatus.NOTIFIED_TO_OFFICIAL, ComplaintStatus.COMMITMENT_PUBLISHED,
    ComplaintStatus.IN_PROGRESS, ComplaintStatus.AWAITING_FIELD_WORK,
    ComplaintStatus.FIELD_WORK_COMPLETED,
    ComplaintStatus.AWAITING_CITIZEN_VERIFICATION,
    ComplaintStatus.REOPENED, ComplaintStatus.ESCALATED,
]


def _parse_commitment_date(raw):
    """Parse a datetime-local input value; returns None when unusable."""
    if not raw:
        return None
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return timezone.make_aware(datetime.datetime.strptime(raw, fmt))
        except ValueError:
            continue
    return None


@login_required
def complaint_action_view(request, complaint_id):
    """Handle all workflow actions POSTed from the complaint detail page."""
    complaint = get_object_or_404(
        Complaint, complaint_id=complaint_id, is_deleted=False
    )
    if request.method != 'POST':
        return redirect('complaint_detail', complaint_id=complaint.complaint_id)
    
    action = request.POST.get('action', '')
    user = request.user
    
    # ------------------------- Phase 3: human review ------------------------
    if action in ('review_approve', 'review_reject', 'review_request_info'):
        if not (user.is_reviewer() or user.is_admin or user.is_superuser):
            messages.error(request, 'Only reviewers and admins can perform this action.')
        elif complaint.status not in (
            ComplaintStatus.PROOF_RECEIVED, ComplaintStatus.AWAITING_HUMAN_REVIEW,
        ):
            messages.error(request, 'This complaint is not awaiting review.')
        else:
            reason = (request.POST.get('reason') or '').strip()
            complaint.human_reviewer = user
            complaint.human_verification_status = action == 'review_approve'
            complaint.human_verification_notes = reason
            complaint.save(update_fields=[
                'human_reviewer', 'human_verification_status',
                'human_verification_notes', 'updated_at',
            ])
            if action == 'review_approve':
                complaint.transition(
                    ComplaintStatus.VERIFIED, changed_by=user,
                    notes=reason or 'Human reviewer approved the complaint',
                )
                # Phase 5: now that a human has verified the evidence, let
                # the routing engine assign a responsible official.
                from apps.ai_services.tasks import route_complaint
                try:
                    route_complaint.delay(complaint.id)
                except Exception:
                    pass
                messages.success(request, 'Complaint approved and handed to the routing engine.')
            elif action == 'review_reject':
                complaint.transition(
                    ComplaintStatus.REJECTED, changed_by=user,
                    notes=reason or 'Rejected during human review',
                )
                messages.success(request, 'Complaint rejected.')
            else:
                complaint.transition(
                    ComplaintStatus.REQUEST_MORE_INFO, changed_by=user,
                    notes=reason or 'More information requested from the citizen',
                )
                messages.success(request, 'More information requested from the citizen.')
    
    # -------------------- Phase 7: public commitment ------------------------
    elif action == 'set_commitment':
        if not (complaint.assigned_official_id == user.id or user.is_admin
                or user.is_superuser or user.is_minister()):
            messages.error(request, 'Only the assigned official can commit.')
        elif complaint.status not in (
            ComplaintStatus.VERIFIED, ComplaintStatus.NOTIFIED_TO_OFFICIAL,
            ComplaintStatus.COMMITMENT_PUBLISHED,
        ):
            messages.error(request, 'Commitment cannot be set at this stage.')
        else:
            commitment = _parse_commitment_date(request.POST.get('commitment_date'))
            if commitment is None:
                messages.error(request, 'Please choose a valid commitment date and time.')
            else:
                complaint.commitment_date = commitment
                complaint.commitment_visible = True
                complaint.save(update_fields=['commitment_date', 'commitment_visible', 'updated_at'])
                complaint.transition(
                    ComplaintStatus.COMMITMENT_PUBLISHED, changed_by=user,
                    notes=f'Public commitment to resolve by {commitment:%b %d, %Y %H:%M}',
                )
                messages.success(request, 'Commitment published publicly.')
    
    # ----------------- Phase 6/10: official progress actions -----------------
    elif action == 'start_progress':
        if not (complaint.assigned_official_id == user.id or user.is_admin or user.is_superuser):
            messages.error(request, 'Only the assigned official can start work.')
        elif complaint.status != ComplaintStatus.COMMITMENT_PUBLISHED:
            messages.error(request, 'Publish a commitment first.')
        else:
            complaint.transition(
                ComplaintStatus.IN_PROGRESS, changed_by=user,
                notes='Official started working on the complaint',
            )
            messages.success(request, 'Complaint marked as in progress.')
    
    elif action == 'release_to_field':
        if not (complaint.assigned_official_id == user.id or user.is_admin or user.is_superuser):
            messages.error(request, 'Only the assigned official can release to field work.')
        elif complaint.status != ComplaintStatus.IN_PROGRESS:
            messages.error(request, 'Start progress before releasing to the field.')
        else:
            field_worker_id = request.POST.get('field_worker')
            if field_worker_id:
                from apps.users.models import CustomUser
                fw = CustomUser.objects.filter(
                    id=field_worker_id, role='FIELD_WORKER'
                ).first()
                if fw:
                    complaint.assigned_field_worker = fw
                    complaint.save(update_fields=['assigned_field_worker', 'updated_at'])
            complaint.transition(
                ComplaintStatus.AWAITING_FIELD_WORK, changed_by=user,
                notes=(f'Released to field work'
                       + (f' (assigned: {complaint.assigned_field_worker.get_short_name()})'
                          if complaint.assigned_field_worker else '')),
            )
            messages.success(request, 'Complaint released to field work.')
    
    # ----------------- Phase 10: field worker completion ---------------------
    elif action == 'complete_field_work':
        if not (complaint.assigned_field_worker_id == user.id or user.is_admin
                or user.is_superuser):
            messages.error(request, 'Only the assigned field worker can complete this.')
        elif complaint.status != ComplaintStatus.AWAITING_FIELD_WORK:
            messages.error(request, 'This complaint is not awaiting field work.')
        else:
            resolution = (request.POST.get('resolution_description') or '').strip()
            complaint.resolution_description = resolution
            complaint.save(update_fields=['resolution_description', 'updated_at'])
            complaint.transition(
                ComplaintStatus.AWAITING_CITIZEN_VERIFICATION, changed_by=user,
                notes='Field work completed; awaiting citizen on-site verification',
            )
            messages.success(request, 'Field work completed - awaiting citizen verification.')
    
    # --------------- Phase 11: citizen on-site verification ------------------
    elif action in ('signoff_satisfied', 'signoff_rework'):
        if not (user.is_citizen() and complaint.citizen_id == user.id):
            messages.error(request, 'Only the citizen who filed this complaint can sign off.')
        elif complaint.status != ComplaintStatus.AWAITING_CITIZEN_VERIFICATION:
            messages.error(request, 'This complaint is not awaiting your verification.')
        else:
            try:
                rating = int(request.POST.get('rating', '0'))
            except ValueError:
                rating = 0
            comment = (request.POST.get('comment') or '').strip()
            if action == 'signoff_satisfied':
                if not 1 <= rating <= 5:
                    messages.error(request, 'Please provide a 1-5 star rating.')
                else:
                    complaint.citizen_verified = True
                    complaint.citizen_verification_date = timezone.now()
                    complaint.citizen_ratings = rating
                    complaint.citizen_comments = comment
                    complaint.resolution_date = timezone.now()
                    complaint.save(update_fields=[
                        'citizen_verified', 'citizen_verification_date',
                        'citizen_ratings', 'citizen_comments',
                        'resolution_date', 'updated_at',
                    ])
                    complaint.transition(
                        ComplaintStatus.RESOLVED, changed_by=user,
                        notes=f'Citizen verified the fix on-site and rated it {rating}/5'
                              + (f' - "{comment}"' if comment else ''),
                    )
                    messages.success(request, 'Thank you! The complaint is now resolved.')
            else:
                reason = comment or 'Citizen requested re-work'
                complaint.citizen_comments = comment
                complaint.citizen_ratings = rating or None
                # Reopen as a task back to the same official; reset the SLA clock
                complaint.sla_deadline = timezone.now() + datetime.timedelta(
                    days=settings.NARADHA['DEFAULT_SLA_DAYS']
                )
                complaint.sla_breached = False
                complaint.days_overdue = 0
                complaint.escalation_level = 0
                complaint.save(update_fields=[
                    'citizen_comments', 'citizen_ratings', 'sla_deadline',
                    'sla_breached', 'days_overdue', 'escalation_level', 'updated_at',
                ])
                complaint.transition(
                    ComplaintStatus.REOPENED, changed_by=user,
                    notes=f'Re-work requested: {reason}',
                )
                messages.success(request, 'Complaint reopened and sent back to the official.')
    
    # --------------- Phase 12: community endorsement --------------------------
    elif action == 'endorse':
        if not user.is_citizen():
            messages.error(request, 'Only citizens can endorse complaints.')
        elif complaint.citizen_id == user.id:
            messages.error(request, 'You cannot endorse your own complaint.')
        elif complaint.status not in OPEN_STATUSES:
            messages.error(request, 'This complaint is closed.')
        else:
            endorsement, created = ComplaintEndorsement.objects.get_or_create(
                complaint=complaint,
                citizen=user,
                defaults={
                    'is_anonymous': bool(request.POST.get('anonymous')),
                    'comments': (request.POST.get('comments') or '').strip(),
                },
            )
            if not created:
                messages.info(request, 'You have already endorsed this complaint.')
            else:
                count = ComplaintEndorsement.objects.filter(complaint=complaint).count()
                complaint.record_status_change(
                    complaint.status,
                    changed_by=user,
                    notes=f'Community endorsement #{count} received',
                )
                # Endorsements strengthen the case: bump priority at 5+
                if count >= 5 and complaint.priority in ('LOW', 'MEDIUM'):
                    complaint.priority = 'HIGH' if complaint.priority == 'MEDIUM' else 'MEDIUM'
                    complaint.save(update_fields=['priority', 'updated_at'])
                messages.success(request, 'Thanks for backing this complaint!')
    
    else:
        messages.error(request, 'Unknown action.')
    
    return redirect('complaint_detail', complaint_id=complaint.complaint_id)
