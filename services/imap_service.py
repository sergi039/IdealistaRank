import os
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from imapclient import IMAPClient
from email import message_from_bytes
from email.header import decode_header
from utils.email_parser import EmailParser
from models import Land
from app import db
from config import Config

logger = logging.getLogger(__name__)

class IMAPService:
    def __init__(self):
        self.host = Config.IMAP_HOST
        self.port = Config.IMAP_PORT
        self.ssl = Config.IMAP_SSL
        self.user = Config.IMAP_USER
        self.password = Config.IMAP_PASSWORD
        self.folder = Config.IMAP_FOLDER
        self.search_query = Config.IMAP_SEARCH_QUERY
        self.max_emails = Config.MAX_EMAILS_PER_RUN
        self.email_parser = EmailParser()
        self.last_seen_uid = self._get_last_seen_uid()
    
    def _get_last_seen_uid(self) -> int:
        """Get the last processed UID from database to avoid reprocessing"""
        try:
            # Check if we have a settings table or use a simple file
            uid_file = ".last_seen_uid"
            if os.path.exists(uid_file):
                with open(uid_file, 'r') as f:
                    return int(f.read().strip() or "0")
            return 0
        except Exception:
            return 0
    
    def _save_last_seen_uid(self, uid: int):
        """Save the last processed UID"""
        try:
            with open(".last_seen_uid", 'w') as f:
                f.write(str(uid))
        except Exception as e:
            logger.error(f"Failed to save last UID: {e}")
    
    def authenticate(self) -> bool:
        """Test IMAP connection and authentication"""
        try:
            if not self.user or not self.password:
                logger.error("IMAP credentials not configured")
                return False
            
            with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
                client.login(self.user, self.password)
                logger.info(f"IMAP authentication successful for {self.user}")
                return True
        except Exception as e:
            logger.error(f"IMAP authentication failed: {str(e)}")
            return False
    
    def _decode_header_value(self, value: str) -> str:
        """Decode email header value"""
        try:
            decoded_parts = decode_header(value)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        result.append(part.decode(encoding, errors='ignore'))
                    else:
                        result.append(part.decode('utf-8', errors='ignore'))
                else:
                    result.append(part)
            return ' '.join(result)
        except Exception:
            return value
    
    def _extract_html_parts(self, msg) -> List[str]:
        """Extract HTML parts from email message"""
        html_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_parts.append(payload.decode('utf-8', errors='ignore'))
        else:
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    html_parts.append(payload.decode('utf-8', errors='ignore'))
        
        return html_parts
    
    def _extract_text_parts(self, msg) -> str:
        """Extract plain text parts from email message"""
        text_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_parts.append(payload.decode('utf-8', errors='ignore'))
        else:
            if msg.get_content_type() == "text/plain":
                payload = msg.get_payload(decode=True)
                if payload:
                    text_parts.append(payload.decode('utf-8', errors='ignore'))
        
        return '\n'.join(text_parts)
    
    def get_idealista_emails(self, max_results: int = None) -> List[Dict]:
        """Fetch and parse Idealista emails via IMAP"""
        if not self.user or not self.password:
            logger.error("IMAP credentials not configured")
            return []
        
        email_data = []
        max_results = max_results or self.max_emails
        
        try:
            with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
                # Login
                client.login(self.user, self.password)
                logger.info(f"Connected to IMAP server as {self.user}")
                
                # Select the folder/label
                try:
                    client.select_folder(self.folder, readonly=True)
                    logger.info(f"Selected folder: {self.folder}")
                except Exception as e:
                    # If label doesn't exist, try INBOX
                    logger.warning(f"Folder '{self.folder}' not found, trying INBOX")
                    client.select_folder("INBOX", readonly=True)
                
                # Search for emails
                if self.search_query == "ALL":
                    # Get all UIDs
                    uids = client.search(['ALL'])
                elif self.search_query == "UNSEEN":
                    uids = client.search(['UNSEEN'])
                else:
                    # Custom search query
                    uids = client.search([self.search_query])
                
                # Filter only new UIDs
                if self.last_seen_uid > 0:
                    uids = [uid for uid in uids if uid > self.last_seen_uid]
                
                # Sort and limit
                uids = sorted(uids)[:max_results]
                
                if not uids:
                    logger.info("No new emails found")
                    return []
                
                logger.info(f"Found {len(uids)} new emails to process")
                
                # Fetch emails
                fetch_data = client.fetch(uids, ['RFC822', 'INTERNALDATE', 'FLAGS'])
                
                for uid in uids:
                    try:
                        raw_email = fetch_data[uid][b'RFC822']
                        msg = message_from_bytes(raw_email)
                        internal_date = fetch_data[uid][b'INTERNALDATE']
                        
                        # Get subject
                        subject = self._decode_header_value(msg.get('Subject', ''))
                        
                        # Skip if not Idealista email
                        if 'idealista' not in subject.lower():
                            continue
                        
                        # Extract HTML content
                        html_parts = self._extract_html_parts(msg)
                        html_body = '\n'.join(html_parts) if html_parts else ''
                        
                        # If no HTML, try text
                        if not html_body:
                            text_body = self._extract_text_parts(msg)
                            if text_body:
                                html_body = text_body
                        
                        if not html_body:
                            logger.warning(f"No content found in email UID {uid}")
                            continue
                        
                        # Parse the email content
                        email_content = {
                            'subject': subject,
                            'body': html_body,
                            'message_id': str(uid)
                        }
                        
                        parsed_data = self.email_parser.parse_idealista_email(email_content)
                        
                        if parsed_data:
                            # Generate unique ID based on email UID
                            parsed_data['source_email_id'] = f"imap_{uid}"
                            parsed_data['email_received_at'] = internal_date
                            email_data.append(parsed_data)
                            logger.info(f"Successfully parsed email UID {uid}: {subject[:50]}...")
                        else:
                            logger.warning(f"Could not parse Idealista data from email UID {uid}")
                        
                        # Update last seen UID
                        self.last_seen_uid = max(self.last_seen_uid, uid)
                        
                    except Exception as e:
                        logger.error(f"Failed to process email UID {uid}: {str(e)}")
                        continue
                
                # Save the last seen UID
                if self.last_seen_uid > 0:
                    self._save_last_seen_uid(self.last_seen_uid)
                    logger.info(f"Saved last seen UID: {self.last_seen_uid}")
                
                logger.info(f"Successfully processed {len(email_data)} Idealista emails")
                
        except Exception as e:
            logger.error(f"Failed to fetch emails via IMAP: {str(e)}")
        
        return email_data
    
    def run_ingestion(self) -> int:
        """Main method to run email ingestion via IMAP"""
        try:
            logger.info("Starting IMAP ingestion process")
            
            # Fetch and parse emails
            emails = self.get_idealista_emails()
            
            if not emails:
                logger.warning("No emails found for ingestion")
                return 0
            
            # Import here to avoid circular imports
            from services.enrichment_service import EnrichmentService
            
            processed_count = 0
            for email_data in emails:
                try:
                    # Check if already exists
                    existing = Land.query.filter_by(
                        source_email_id=email_data['source_email_id']
                    ).first()
                    
                    if existing:
                        logger.debug(f"Email {email_data['source_email_id']} already processed")
                        continue
                    
                    # Create new land record
                    land = Land(
                        source_email_id=email_data['source_email_id'],
                        title=email_data.get('title'),
                        url=email_data.get('url'),
                        price=email_data.get('price'),
                        area=email_data.get('area'),
                        municipality=email_data.get('municipality'),
                        land_type=email_data.get('land_type'),
                        description=email_data.get('description'),
                        legal_status=email_data.get('legal_status')
                    )
                    
                    db.session.add(land)
                    db.session.commit()
                    
                    # Enrich the land data
                    enrichment_service = EnrichmentService()
                    enrichment_service.enrich_land(land.id)
                    
                    processed_count += 1
                    logger.info(f"Processed new land: {land.title}")
                    
                except Exception as e:
                    logger.error(f"Failed to process email {email_data.get('source_email_id')}: {str(e)}")
                    db.session.rollback()
                    continue
            
            logger.info(f"IMAP ingestion completed. Processed {processed_count} new properties")
            return processed_count
            
        except Exception as e:
            logger.error(f"IMAP ingestion failed: {str(e)}")
            return 0