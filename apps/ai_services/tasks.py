"""
Celery tasks for AI services.
"""
import os
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from celery import shared_task
from django.db.models import F
from .models import (
    AIServiceLog, ImageAnalysisResult, TextAnalysisResult,
    PriorityScoringResult, RoutingSuggestion
)
from apps.complaints.models import Complaint, ComplaintProof, ComplaintHistory
from apps.users.models import CustomUser, Department, Jurisdiction
from apps.verification.models import VerificationResult
from apps.routing.models import RoutingLog, OfficialWorkload


@shared_task(bind=True, max_retries=3)
def verify_complaint_proofs(self, complaint_id):
    """Verify complaint proofs using AI."""
    try:
        complaint = Complaint.objects.get(id=complaint_id)
        proofs = complaint.proofs.all()
        
        if not proofs.exists():
            # No proofs to verify
            complaint.ai_verification_status = True
            complaint.ai_confidence_score = 0
            complaint.save()
            return {'status': 'SUCCESS', 'message': 'No proofs to verify'}
        
        # Process each proof
        total_score = 0
        proof_count = 0
        
        for proof in proofs:
            try:
                # Analyze image
                result = analyze_image(proof)
                
                # Update proof with analysis results
                proof.ai_analysis_complete = True
                proof.ai_authenticity_score = result.get('authenticity_score', 0)
                proof.ai_relevance_score = result.get('relevance_score', 0)
                proof.ai_quality_score = result.get('quality_score', 0)
                proof.ai_manipulation_detected = result.get('manipulation_detected', False)
                proof.ai_manipulation_confidence = result.get('manipulation_confidence', 0)
                proof.ai_notes = result.get('notes', '')
                proof.save()
                
                # Save detailed analysis result
                ImageAnalysisResult.objects.update_or_create(
                    proof=proof,
                    defaults={
                        'analysis_complete': True,
                        'image_width': result.get('width', 0),
                        'image_height': result.get('height', 0),
                        'image_format': result.get('format', ''),
                        'camera_make': result.get('camera_make', ''),
                        'camera_model': result.get('camera_model', ''),
                        'capture_timestamp': result.get('capture_timestamp'),
                        'gps_latitude': result.get('gps_latitude'),
                        'gps_longitude': result.get('gps_longitude'),
                        'gps_accuracy': result.get('gps_accuracy'),
                        'quality_score': result.get('quality_score', 0),
                        'blur_score': result.get('blur_score', 0),
                        'brightness_score': result.get('brightness_score', 0),
                        'contrast_score': result.get('contrast_score', 0),
                        'manipulation_detected': result.get('manipulation_detected', False),
                        'manipulation_confidence': result.get('manipulation_confidence', 0),
                        'manipulation_type': result.get('manipulation_type', ''),
                        'relevance_score': result.get('relevance_score', 0),
                        'relevance_keywords': result.get('relevance_keywords', []),
                        'authenticity_score': result.get('authenticity_score', 0),
                        'authenticity_notes': result.get('notes', ''),
                    }
                )
                
                total_score += result.get('authenticity_score', 0)
                proof_count += 1
                
            except Exception as e:
                # Log error but continue with other proofs
                AIServiceLog.objects.create(
                    service_name='verify_complaint_proofs',
                    proof=proof,
                    request_data={'complaint_id': complaint_id, 'proof_id': proof.id},
                    response_data={'error': str(e)},
                    status='ERROR',
                    error_message=str(e)
                )
                continue
        
        # Calculate average score
        avg_score = total_score / proof_count if proof_count > 0 else 0
        
        # Update complaint (audit-trailed transition; never regress the status
        # if the complaint has already moved further along the workflow)
        complaint.ai_verification_status = True
        complaint.ai_confidence_score = avg_score
        complaint.save(update_fields=['ai_verification_status', 'ai_confidence_score', 'updated_at'])
        if complaint.status in ('DRAFT', 'SUBMITTED'):
            complaint.transition(
                'PROOF_RECEIVED',
                notes=(f'AI verified {proof_count} evidence file(s); '
                       f'confidence {avg_score:.0f}%'),
            )
        
        # Create verification result
        VerificationResult.objects.update_or_create(
            complaint=complaint,
            defaults={
                'ai_verification_passed': avg_score >= settings.NARADHA['AI_CONFIDENCE_THRESHOLD'],
                'ai_confidence_score': avg_score,
                'ai_verified_at': timezone.now()
            }
        )
        
        # Log service call
        AIServiceLog.objects.create(
            service_name='verify_complaint_proofs',
            complaint=complaint,
            request_data={'complaint_id': complaint_id},
            response_data={'avg_score': avg_score, 'proof_count': proof_count},
            status='SUCCESS',
            processing_time=1.0
        )
        
        return {'status': 'SUCCESS', 'avg_score': avg_score, 'proof_count': proof_count}
        
    except Complaint.DoesNotExist:
        return {'status': 'ERROR', 'message': 'Complaint not found'}
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {'status': 'ERROR', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def score_complaint_priority(self, complaint_id):
    """Score complaint priority using AI."""
    try:
        complaint = Complaint.objects.get(id=complaint_id)
        
        # Analyze text
        text_result = analyze_text(complaint.description)
        
        # Save text analysis result
        TextAnalysisResult.objects.update_or_create(
            complaint=complaint,
            defaults={
                'analysis_complete': True,
                'text_length': len(complaint.description),
                'word_count': len(complaint.description.split()),
                'sentence_count': complaint.description.count('.') + complaint.description.count('!') + complaint.description.count('?'),
                'detected_language': text_result.get('language', 'en'),
                'language_confidence': text_result.get('language_confidence', 0),
                'sentiment_score': text_result.get('sentiment_score', 0),
                'sentiment_label': text_result.get('sentiment_label', 'NEUTRAL'),
                'sentiment_confidence': text_result.get('sentiment_confidence', 0),
                'emotions': text_result.get('emotions', {}),
                'keywords': text_result.get('keywords', []),
                'keyword_scores': text_result.get('keyword_scores', {}),
                'primary_topic': text_result.get('primary_topic', ''),
                'secondary_topics': text_result.get('secondary_topics', []),
                'entities': text_result.get('entities', {}),
                'urgency_score': text_result.get('urgency_score', 0),
                'urgency_keywords': text_result.get('urgency_keywords', []),
                'severity_score': text_result.get('severity_score', 0),
                'severity_indicators': text_result.get('severity_indicators', []),
            }
        )
        
        # Calculate priority score
        priority_score = calculate_priority_score(complaint, text_result)
        
        # Update complaint
        complaint.priority_score = priority_score
        
        # Determine priority level
        thresholds = settings.NARADHA['PRIORITY_THRESHOLDS']
        if priority_score >= thresholds['CRITICAL']:
            complaint.priority = 'CRITICAL'
        elif priority_score >= thresholds['HIGH']:
            complaint.priority = 'HIGH'
        elif priority_score >= thresholds['MEDIUM']:
            complaint.priority = 'MEDIUM'
        else:
            complaint.priority = 'LOW'
        
        complaint.save()
        
        # SLA reference point (Phase 7): the deadline is fixed when the
        # complaint is first AI-verified, independent of the official's
        # commitment date, so breach detection always has a baseline.
        if complaint.sla_deadline is None:
            complaint.sla_deadline = timezone.now() + timedelta(
                days=settings.NARADHA['DEFAULT_SLA_DAYS']
            )
            complaint.save(update_fields=['sla_deadline', 'updated_at'])
        
        # Save priority scoring result
        PriorityScoringResult.objects.update_or_create(
            complaint=complaint,
            defaults={
                'base_score': text_result.get('base_score', 0),
                'urgency_score': text_result.get('urgency_score', 0),
                'severity_score': text_result.get('severity_score', 0),
                'impact_score': text_result.get('impact_score', 0),
                'recurrence_score': 0,  # Will be calculated separately
                'evidence_score': complaint.ai_confidence_score / 10,  # Normalize to 0-10
                'final_score': priority_score,
                'priority_level': complaint.priority,
                'factors': {
                    'text_analysis': text_result,
                    'ai_confidence': complaint.ai_confidence_score,
                    'category_weight': complaint.category.priority_weight if complaint.category else 1
                }
            }
        )
        
        # Update complaint status
        if complaint.ai_verification_status and complaint.priority_score > 0:
            if complaint.status == 'PROOF_RECEIVED':
                complaint.transition(
                    'AWAITING_HUMAN_REVIEW',
                    notes=(f'AI priority {priority_score:g}/10 ({complaint.priority}); '
                           f'sentiment {text_result.get("sentiment_label", "NEUTRAL")}, '
                           f'urgency {text_result.get("urgency_score", 0):.0f}%'),
                )
            else:
                complaint.save(update_fields=['priority_score', 'priority', 'updated_at'])
        
        # Log service call
        AIServiceLog.objects.create(
            service_name='score_complaint_priority',
            complaint=complaint,
            request_data={'complaint_id': complaint_id},
            response_data={'priority_score': priority_score, 'priority_level': complaint.priority},
            status='SUCCESS'
        )
        
        return {'status': 'SUCCESS', 'priority_score': priority_score, 'priority_level': complaint.priority}
        
    except Complaint.DoesNotExist:
        return {'status': 'ERROR', 'message': 'Complaint not found'}
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {'status': 'ERROR', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def route_complaint(self, complaint_id):
    """Route complaint to appropriate official using AI."""
    try:
        complaint = Complaint.objects.get(id=complaint_id)
        
        # Check if already routed
        if complaint.assigned_official:
            return {'status': 'SUCCESS', 'message': 'Already routed'}
        
        # Get routing suggestion
        suggestion = get_routing_suggestion(complaint)
        
        # Save routing suggestion
        RoutingSuggestion.objects.update_or_create(
            complaint=complaint,
            defaults={
                'suggested_department': suggestion.get('department'),
                'suggested_jurisdiction': suggestion.get('jurisdiction'),
                'department_confidence': suggestion.get('department_confidence', 0),
                'jurisdiction_confidence': suggestion.get('jurisdiction_confidence', 0),
                'reasoning': suggestion.get('reasoning', ''),
            }
        )
        
        # Assign to official
        official = suggestion.get('official')
        department = suggestion.get('department')
        
        if official and department:
            previous_status = complaint.status
            complaint.assigned_official = official
            complaint.assigned_department = department
            complaint.status = 'NOTIFIED_TO_OFFICIAL'
            complaint.save()
            
            # Create history record
            ComplaintHistory.objects.create(
                complaint=complaint,
                previous_status=previous_status,
                new_status='NOTIFIED_TO_OFFICIAL',
                changed_by=None,  # System assigned
                notes=(f'Auto-routed to {official.get_short_name()} ({department.name}); '
                       f'SLA deadline {complaint.sla_deadline:%b %d, %Y}' if complaint.sla_deadline else
                       f'Auto-routed to {official.get_short_name()} ({department.name})')
            )
            
            # Log routing
            RoutingLog.objects.create(
                complaint=complaint,
                previous_official=None,
                new_official=official,
                new_department=department,
                routing_method='AUTO',
                routing_reason=suggestion.get('reasoning', 'AI routing')
            )
            
            # Update official workload
            OfficialWorkload.objects.update_or_create(
                official=official,
                defaults={
                    'assigned_complaints': F('assigned_complaints') + 1
                }
            )
            
            return {
                'status': 'SUCCESS',
                'official': official.id,
                'department': department.id,
                'confidence': suggestion.get('confidence', 0)
            }
        else:
            # Could not find suitable official
            complaint.status = 'VERIFIED'
            complaint.save()
            
            return {
                'status': 'PARTIAL',
                'message': 'Could not find suitable official for auto-routing'
            }
        
    except Complaint.DoesNotExist:
        return {'status': 'ERROR', 'message': 'Complaint not found'}
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {'status': 'ERROR', 'message': str(e)}


@shared_task(bind=True, max_retries=3)
def check_sla_breaches(self):
    """Check for SLA breaches and escalate if needed."""
    from apps.complaints.models import Complaint
    from apps.messaging.models import Notification
    from datetime import timedelta
    
    try:
        # Get complaints that are overdue
        overdue_complaints = Complaint.objects.filter(
            sla_deadline__isnull=False,
            sla_deadline__lte=timezone.now(),
            status__in=['COMMITMENT_PUBLISHED', 'IN_PROGRESS', 'AWAITING_FIELD_WORK'],
            sla_breached=False
        )
        
        for complaint in overdue_complaints:
            # Calculate days overdue
            days_overdue = (timezone.now() - complaint.sla_deadline).days
            
            # Update complaint
            complaint.sla_breached = True
            complaint.days_overdue = days_overdue
            
            # Escalate based on level
            if complaint.escalation_level == 0:
                # Level 1: Notify supervisor
                supervisor = get_supervisor(complaint.assigned_official)
                if supervisor:
                    complaint.escalated_to = supervisor
                    complaint.escalation_level = 1
                    complaint.escalation_date = timezone.now()
                    complaint.escalation_reason = f'SLA breached by {days_overdue} days'
            elif complaint.escalation_level == 1:
                # Level 2: Notify department head
                dept_head = get_department_head(complaint.assigned_department)
                if dept_head:
                    complaint.escalated_to = dept_head
                    complaint.escalation_level = 2
                    complaint.escalation_date = timezone.now()
                    complaint.escalation_reason = f'SLA breached by {days_overdue} days'
            elif complaint.escalation_level == 2:
                # Level 3: Notify minister
                minister = get_minister_for_department(complaint.assigned_department)
                if minister:
                    complaint.escalated_to = minister
                    complaint.escalation_level = 3
                    complaint.escalation_date = timezone.now()
                    complaint.escalation_reason = f'SLA breached by {days_overdue} days'
            else:
                # Level 4: State level escalation
                complaint.escalation_level = 4
                complaint.escalation_date = timezone.now()
                complaint.escalation_reason = f'SLA breached by {days_overdue} days - State level'
            
            complaint.status = 'ESCALATED'
            complaint.save()
            
            # Create notification
            Notification.objects.create(
                user=complaint.escalated_to,
                notification_type='ESCALATION',
                complaint=complaint,
                title=f'SLA Breach: Complaint {complaint.complaint_id}',
                body=f'Complaint {complaint.complaint_id} has breached SLA by {days_overdue} days.',
                priority='URGENT',
                delivered_via_app=True
            )
            
            # Log the escalation
            ComplaintHistory.objects.create(
                complaint=complaint,
                previous_status='IN_PROGRESS',
                new_status='ESCALATED',
                changed_by=None,
                notes=f'Auto-escalated due to SLA breach ({days_overdue} days overdue)'
            )
        
        return {'status': 'SUCCESS', 'escalated_count': overdue_complaints.count()}
        
    except Exception as e:
        self.retry(exc=e, countdown=60)
        return {'status': 'ERROR', 'message': str(e)}


# Helper functions

def analyze_image(proof):
    """Analyze an image proof."""
    result = {
        'authenticity_score': 0,
        'relevance_score': 0,
        'quality_score': 0,
        'manipulation_detected': False,
        'manipulation_confidence': 0,
        'notes': '',
        'width': 0,
        'height': 0,
        'format': '',
        'camera_make': '',
        'camera_model': '',
        'capture_timestamp': None,
        'gps_latitude': None,
        'gps_longitude': None,
        'gps_accuracy': None,
        'blur_score': 0,
        'brightness_score': 0,
        'contrast_score': 0,
        'manipulation_type': '',
        'relevance_keywords': [],
    }
    
    try:
        # Open the image
        img_path = proof.file.path
        
        # Check if file exists
        if not os.path.exists(img_path):
            return result
        
        # Use OpenCV to analyze
        img = cv2.imread(img_path)
        
        if img is not None:
            result['width'] = img.shape[1]
            result['height'] = img.shape[0]
            
            # Check for blur
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
            result['blur_score'] = min(100, blur_score * 100 / 1000)  # Normalize
            
            # Check brightness
            brightness = cv2.mean(gray)[0]
            result['brightness_score'] = min(100, brightness * 100 / 255)
            
            # Check contrast
            contrast = float(gray.std())
            result['contrast_score'] = min(100, contrast * 100 / 128)
            
            # Quality score (combination of factors)
            result['quality_score'] = (
                (100 - result['blur_score']) * 0.4 +
                result['brightness_score'] * 0.3 +
                result['contrast_score'] * 0.3
            )
            
            # Try to extract metadata
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS
                
                pil_img = Image.open(img_path)
                exif_data = pil_img._getexif() or {}
                
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'Make':
                        result['camera_make'] = str(value)
                    elif tag == 'Model':
                        result['camera_model'] = str(value)
                    elif tag == 'DateTime':
                        try:
                            result['capture_timestamp'] = datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                        except:
                            pass
                    elif tag == 'GPSInfo':
                        # Extract GPS coordinates
                        try:
                            gps_data = {}
                            if 1 in value:  # GPSLatitude
                                lat = value[1]
                                lat_ref = value[3] if 3 in value else 'N'
                                gps_data['latitude'] = convert_gps_coordinate(lat, lat_ref)
                            if 3 in value:  # GPSLongitude
                                lon = value[5]
                                lon_ref = value[7] if 7 in value else 'E'
                                gps_data['longitude'] = convert_gps_coordinate(lon, lon_ref)
                            
                            if 'latitude' in gps_data and 'longitude' in gps_data:
                                result['gps_latitude'] = gps_data['latitude']
                                result['gps_longitude'] = gps_data['longitude']
                        except:
                            pass
            except Exception as e:
                # Could not extract metadata
                pass
            
            # Check for manipulation (simplified)
            # In production, use more sophisticated methods
            result['manipulation_detected'] = False
            result['manipulation_confidence'] = 0
            
            # Authenticity score (based on metadata and quality)
            authenticity_factors = [
                result['quality_score'] * 0.4,
                (100 if result['camera_make'] else 0) * 0.2,
                (100 if result['capture_timestamp'] else 0) * 0.2,
                (100 if result['gps_latitude'] else 0) * 0.2
            ]
            result['authenticity_score'] = sum(authenticity_factors) / len(authenticity_factors)
            
            # Relevance score (based on complaint category)
            complaint = proof.complaint
            if complaint.category:
                # Check if image matches category
                category_keywords = {
                    'Roads': ['road', 'pothole', 'crack', 'pavement', 'street'],
                    'Sanitation': ['garbage', 'waste', 'trash', 'dirty', 'clean'],
                    'Water Supply': ['water', 'pipe', 'leak', 'tank', 'pump'],
                    'Electricity': ['electric', 'wire', 'pole', 'light', 'power'],
                }
                
                keywords = category_keywords.get(complaint.category.name, [])
                result['relevance_keywords'] = keywords
                result['relevance_score'] = 70  # Default relevance
            else:
                result['relevance_score'] = 50
        
        result['format'] = proof.file_type
        
    except Exception as e:
        result['notes'] = f'Error analyzing image: {str(e)}'
    
    return result


def convert_gps_coordinate(coord, ref):
    """Convert GPS coordinate from EXIF format to decimal."""
    degrees = coord[0][0] / coord[0][1]
    minutes = coord[1][0] / coord[1][1]
    seconds = coord[2][0] / coord[2][1]
    
    decimal = degrees + (minutes / 60) + (seconds / 3600)
    
    if ref in ['S', 'W']:
        decimal = -decimal
    
    return decimal


def analyze_text(text):
    """Analyze complaint text."""
    result = {
        'language': 'en',
        'language_confidence': 100,
        'sentiment_score': 0,
        'sentiment_label': 'NEUTRAL',
        'sentiment_confidence': 0,
        'emotions': {},
        'keywords': [],
        'keyword_scores': {},
        'primary_topic': '',
        'secondary_topics': [],
        'entities': {},
        'urgency_score': 0,
        'urgency_keywords': [],
        'severity_score': 0,
        'severity_indicators': [],
        'base_score': 0,
        'impact_score': 0,
    }
    
    try:
        if not text:
            return result
        
        # Language detection (simplified)
        result['language'] = 'en'
        result['language_confidence'] = 100
        
        # Sentiment analysis (simplified)
        text_lower = text.lower()
        
        positive_words = ['good', 'great', 'excellent', 'well', 'fixed', 'resolved']
        negative_words = ['bad', 'poor', 'broken', 'damaged', 'dangerous', 'urgent', 'emergency']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        result['sentiment_score'] = (positive_count - negative_count) / max(len(text_lower.split()), 1)
        
        if result['sentiment_score'] > 0.1:
            result['sentiment_label'] = 'POSITIVE'
        elif result['sentiment_score'] < -0.1:
            result['sentiment_label'] = 'NEGATIVE'
        else:
            result['sentiment_label'] = 'NEUTRAL'
        
        result['sentiment_confidence'] = abs(result['sentiment_score']) * 100
        
        # Emotion detection (simplified)
        emotions = {
            'anger': sum(1 for word in ['angry', 'furious', 'outrage'] if word in text_lower),
            'fear': sum(1 for word in ['danger', 'risk', 'unsafe', 'hazard'] if word in text_lower),
            'sadness': sum(1 for word in ['sad', 'upset', 'disappointed'] if word in text_lower),
            'joy': sum(1 for word in ['happy', 'pleased', 'satisfied'] if word in text_lower),
        }
        
        total_emotions = sum(emotions.values())
        if total_emotions > 0:
            for emotion, count in emotions.items():
                result['emotions'][emotion] = count / total_emotions
        
        # Keyword extraction
        words = text_lower.split()
        word_freq = {}
        for word in words:
            word = word.strip('.,!?;:()[]{}"\'')
            if len(word) > 3:  # Ignore short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        result['keywords'] = [word for word, count in sorted_words[:10]]
        result['keyword_scores'] = {word: count for word, count in sorted_words[:20]}
        
        # Urgency analysis
        urgency_keywords = {
            'emergency': 10,
            'urgent': 8,
            'danger': 9,
            'risk': 7,
            'immediate': 8,
            'accident': 10,
            'injury': 9,
            'broken': 5,
            'damaged': 5,
            'blocked': 6,
        }
        
        urgency_score = 0
        for word, score in urgency_keywords.items():
            if word in text_lower:
                urgency_score += score
                result['urgency_keywords'].append(word)
        
        result['urgency_score'] = min(100, urgency_score * 5)
        
        # Severity analysis
        severity_indicators = {
            'fatal': 10,
            'dead': 10,
            'injured': 8,
            'collapsed': 9,
            'flood': 8,
            'fire': 9,
            'explosion': 10,
            'epidemic': 9,
            'disease': 7,
        }
        
        severity_score = 0
        for word, score in severity_indicators.items():
            if word in text_lower:
                severity_score += score
                result['severity_indicators'].append(word)
        
        result['severity_score'] = min(100, severity_score * 5)
        
        # Base score (length and detail)
        result['base_score'] = min(10, len(text) / 100) * 10
        
        # Impact score (based on words like 'many', 'several', 'all')
        impact_words = ['many', 'several', 'all', 'everyone', 'entire', 'whole']
        impact_score = sum(1 for word in impact_words if word in text_lower) * 10
        result['impact_score'] = min(100, impact_score * 5)
        
        # Primary topic (simplified)
        topic_keywords = {
            'Roads': ['road', 'pothole', 'street', 'pavement', 'traffic'],
            'Sanitation': ['garbage', 'waste', 'trash', 'clean', 'dirty', 'sewage'],
            'Water Supply': ['water', 'pipe', 'leak', 'tank', 'pump', 'supply'],
            'Electricity': ['electric', 'wire', 'pole', 'light', 'power', 'current'],
        }
        
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for word in keywords if word in text_lower)
            topic_scores[topic] = score
        
        if topic_scores:
            primary_topic = max(topic_scores.items(), key=lambda x: x[1])
            result['primary_topic'] = primary_topic[0]
            
            # Get secondary topics
            sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
            result['secondary_topics'] = [topic for topic, score in sorted_topics[1:3] if score > 0]
        
        # Entity recognition (simplified)
        # Look for patterns like dates, times, locations
        result['entities'] = {
            'DATE': [],
            'TIME': [],
            'LOCATION': [],
            'PERSON': [],
            'ORGANIZATION': []
        }
        
    except Exception as e:
        result['notes'] = f'Error analyzing text: {str(e)}'
    
    return result


def calculate_priority_score(complaint, text_result):
    """Calculate priority score for a complaint."""
    # Get category weight
    category_weight = complaint.category.priority_weight if complaint.category else 1
    
    # Get base score from text analysis
    base_score = text_result.get('base_score', 0)
    urgency_score = text_result.get('urgency_score', 0)
    severity_score = text_result.get('severity_score', 0)
    impact_score = text_result.get('impact_score', 0)
    
    # Get AI confidence score
    ai_score = complaint.ai_confidence_score / 10  # Normalize to 0-10
    
    # Calculate weights
    total_weight = 0.4 + 0.3 + 0.2 + 0.1  # Adjust as needed
    
    # Calculate score
    score = (
        base_score * 0.1 +
        urgency_score * 0.4 +
        severity_score * 0.3 +
        impact_score * 0.2 +
        ai_score * 0.1
    )
    
    # Multiply by category weight
    score *= category_weight
    
    # Ensure score is between 1 and 10
    score = max(1, min(10, score / 10))
    
    return round(score, 2)


def get_routing_suggestion(complaint):
    """Get routing suggestion for a complaint."""
    result = {
        'department': None,
        'jurisdiction': None,
        'official': None,
        'department_confidence': 0,
        'jurisdiction_confidence': 0,
        'confidence': 0,
        'reasoning': '',
        'officials_confidence': {}
    }
    
    try:
        # Determine department based on category
        if complaint.category and complaint.category.department:
            result['department'] = complaint.category.department
            result['department_confidence'] = 100
        
        # Determine jurisdiction from complaint
        if complaint.jurisdiction:
            result['jurisdiction'] = complaint.jurisdiction
            result['jurisdiction_confidence'] = 100
        
        # Find suitable official
        if result['department']:
            officials = CustomUser.objects.filter(
                role='OFFICIAL',
                department=result['department'],
                is_active=True
            )
            
            if result['jurisdiction']:
                officials = officials.filter(jurisdiction=result['jurisdiction'])
            
            # Get least busy official
            if officials.exists():
                # Get workloads
                workloads = OfficialWorkload.objects.filter(official__in=officials)
                workload_dict = {w.official_id: w.load_score for w in workloads}
                
                # Sort by load score
                sorted_officials = sorted(
                    officials,
                    key=lambda o: workload_dict.get(o.id, 0)
                )
                
                result['official'] = sorted_officials[0]
                
                # Calculate confidence
                result['confidence'] = 90  # High confidence in routing
                result['reasoning'] = (
                    f"Complaint category '{complaint.category.name}' maps to department "
                    f"'{result['department'].name}'. "
                    f"Selected least busy official in the department."
                )
                
                # Confidence for each official
                for official in sorted_officials[:5]:
                    result['officials_confidence'][official.id] = 100 - workload_dict.get(official.id, 0)
        
    except Exception as e:
        result['reasoning'] = f'Error in routing: {str(e)}'
    
    return result


def get_supervisor(official):
    """Get supervisor for an official."""
    # In production, this would query the organizational hierarchy
    # For now, return the first admin user
    return CustomUser.objects.filter(
        role__in=['ADMIN', 'MINISTER'],
        department=official.department
    ).first()


def get_department_head(department):
    """Get department head."""
    return CustomUser.objects.filter(
        role='MINISTER',
        department=department
    ).first()


def get_minister_for_department(department):
    """Get minister for a department."""
    return CustomUser.objects.filter(
        role='MINISTER',
        department=department
    ).first()
