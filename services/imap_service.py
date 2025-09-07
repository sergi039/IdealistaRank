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
                client.login(self.user, self.password)
                logger.info(f"Connected to IMAP server as {self.user}")

                # Gmail: работаем из All Mail, ярлык — через X-GM-RAW
                if 'gmail' in self.host.lower():
                    try:
                        client.select_folder('[Gmail]/All Mail', readonly=True)
                        logger.info("Selected [Gmail]/All Mail")
                    except Exception:
                        client.select_folder('INBOX', readonly=True)
                        logger.info("Fallback to INBOX")
                    # Упрощенный поиск - только по отправителю
                    gm_query = 'from:noresponder@idealista.com'
                    try:
                        uids = client.search(['X-GM-RAW', gm_query])
                        logger.info(f"Gmail X-GM-RAW search found {len(uids)} emails")
                    except Exception as e:
                        logger.warning(f"X-GM-RAW not available: {e}, falling back to ALL")
                        uids = client.search(['ALL'])
                else:
                    client.select_folder(self.folder or "INBOX", readonly=True)
                    uids = client.search(['ALL'])

                logger.info(f"Total emails found: {len(uids)}")

                if self.last_seen_uid > 0:
                    uids = [u for u in uids if u > self.last_seen_uid]
                    logger.info(f"Filtering by last_seen_uid ({self.last_seen_uid}): {len(uids)} new emails")
                    
                # Ограничим первую обработку 5 письмами для теста
                uids = sorted(uids)[:5] if max_results is None else sorted(uids)[:max_results]
                if not uids:
                    logger.info("No new emails found")
                    return []

                logger.info(f"Processing {len(uids)} emails...")
                fetch_data = client.fetch(uids, ['RFC822', 'INTERNALDATE'])
                
                for uid in uids:
                    try:
                        raw_email = fetch_data[uid][b'RFC822']
                        msg = message_from_bytes(raw_email)

                        html_parts = self._extract_html_parts(msg)
                        body = '\n'.join(html_parts) or self._extract_text_parts(msg)
                        if not body:
                            logger.warning(f"No body found in email UID {uid}")
                            continue

                        subject = self._decode_header_value(msg.get('Subject', ''))
                        logger.info(f"Processing email UID {uid}: {subject[:50]}...")
                        
                        email_content = {'subject': subject, 'body': body, 'message_id': f"imap_{uid}"}
                        parsed = self.email_parser.parse_idealista_email(email_content)
                        if parsed:
                            parsed['source_email_id'] = f"imap_{uid}"
                            parsed['email_received_at'] = fetch_data[uid][b'INTERNALDATE']
                            email_data.append(parsed)
                            logger.info(f"Successfully parsed email UID {uid}")
                        else:
                            logger.warning(f"Could not parse Idealista data from email UID {uid}")
                    except Exception as e:
                        logger.error(f"Failed to process UID {uid}: {e}")
                        continue

                # Persist last seen
                if uids:
                    self.last_seen_uid = max(uids)
                    self._save_last_seen_uid(self.last_seen_uid)
                    logger.info(f"Saved last seen UID: {self.last_seen_uid}")

                logger.info(f"Successfully processed {len(email_data)} Idealista emails")

        except Exception as e:
            logger.error(f"Failed to fetch via IMAP: {e}")

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
                    
                    # Temporarily skip enrichment to avoid timeouts
                    # enrichment_service = EnrichmentService()
                    # enrichment_service.enrich_land(land.id)
                    logger.info(f"Skipping enrichment for land {land.id} to avoid timeouts")
                    
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