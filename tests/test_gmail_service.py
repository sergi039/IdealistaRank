"""
Tests for Gmail service functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app import create_app, db
from models import Land
from services.gmail_service import GmailService
from tests import setup_test_environment


@pytest.fixture
def app():
    """Create test Flask application"""
    setup_test_environment()
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def gmail_service():
    """Create GmailService instance"""
    return GmailService()


class TestGmailService:
    """Test cases for Gmail service"""
    
    def test_init(self, gmail_service):
        """Test GmailService initialization"""
        assert gmail_service.service is None
        assert gmail_service.email_parser is not None
        assert hasattr(gmail_service, 'SCOPES')
        assert 'gmail.readonly' in gmail_service.SCOPES[0]
    
    @patch.dict('os.environ', {'GMAIL_API_KEY': 'test_key'})
    @patch('services.gmail_service.build')
    def test_authenticate_success(self, mock_build, gmail_service):
        """Test successful authentication"""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = gmail_service.authenticate()
        
        assert result is True
        assert gmail_service.service == mock_service
        mock_build.assert_called_once_with('gmail', 'v1', developerKey='test_key')
    
    @patch.dict('os.environ', {}, clear=True)
    def test_authenticate_no_api_key(self, gmail_service):
        """Test authentication failure with no API key"""
        result = gmail_service.authenticate()
        
        assert result is False
        assert gmail_service.service is None
    
    @patch.dict('os.environ', {'GMAIL_API_KEY': 'test_key'})
    @patch('services.gmail_service.build')
    def test_authenticate_exception(self, mock_build, gmail_service):
        """Test authentication failure with exception"""
        mock_build.side_effect = Exception("API Error")
        
        result = gmail_service.authenticate()
        
        assert result is False
        assert gmail_service.service is None
    
    def test_get_idealista_emails_no_service(self, gmail_service):
        """Test get_idealista_emails without authenticated service"""
        result = gmail_service.get_idealista_emails()
        
        assert result == []
    
    @patch('services.gmail_service.GmailService.authenticate')
    def test_get_idealista_emails_auth_failure(self, mock_auth, gmail_service):
        """Test get_idealista_emails with authentication failure"""
        mock_auth.return_value = False
        
        result = gmail_service.get_idealista_emails()
        
        assert result == []
        mock_auth.assert_called_once()
    
    @patch('services.gmail_service.GmailService.get_email_content')
    @patch('services.gmail_service.GmailService.authenticate')
    def test_get_idealista_emails_success(self, mock_auth, mock_get_content, gmail_service):
        """Test successful retrieval of Idealista emails"""
        # Setup mocks
        mock_auth.return_value = True
        mock_service = Mock()
        gmail_service.service = mock_service
        
        # Mock Gmail API response
        mock_messages_list = Mock()
        mock_service.users.return_value.messages.return_value.list.return_value = mock_messages_list
        mock_messages_list.execute.return_value = {
            'messages': [
                {'id': 'msg_1'},
                {'id': 'msg_2'}
            ]
        }
        
        # Mock email content and parser
        mock_get_content.side_effect = [
            {
                'subject': 'Nueva propiedad en Valencia',
                'body': 'Terreno urbano 1500m² 150000€',
                'message_id': 'msg_1'
            },
            {
                'subject': 'Terreno en Madrid',
                'body': 'Parcela urbanizable 2000m² 200000€',
                'message_id': 'msg_2'
            }
        ]
        
        # Mock parser responses
        with patch.object(gmail_service.email_parser, 'parse_idealista_email') as mock_parser:
            mock_parser.side_effect = [
                {
                    'title': 'Nueva propiedad en Valencia',
                    'price': 150000.0,
                    'area': 1500.0,
                    'land_type': 'developed',
                    'municipality': 'Valencia'
                },
                {
                    'title': 'Terreno en Madrid',
                    'price': 200000.0,
                    'area': 2000.0,
                    'land_type': 'buildable',
                    'municipality': 'Madrid'
                }
            ]
            
            result = gmail_service.get_idealista_emails()
            
            assert len(result) == 2
            assert result[0]['source_email_id'] == 'msg_1'
            assert result[1]['source_email_id'] == 'msg_2'
            assert result[0]['title'] == 'Nueva propiedad en Valencia'
            assert result[1]['title'] == 'Terreno en Madrid'
    
    def test_get_email_content_success(self, gmail_service):
        """Test successful email content retrieval"""
        # Setup mock service
        mock_service = Mock()
        gmail_service.service = mock_service
        
        # Mock API response
        mock_message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@idealista.com'}
                ],
                'body': {
                    'data': 'VGVzdCBib2R5IGNvbnRlbnQ='  # Base64 encoded "Test body content"
                }
            }
        }
        
        mock_get = Mock()
        mock_service.users.return_value.messages.return_value.get.return_value = mock_get
        mock_get.execute.return_value = mock_message
        
        result = gmail_service.get_email_content('test_message_id')
        
        assert result is not None
        assert result['subject'] == 'Test Subject'
        assert result['body'] == 'Test body content'
        assert result['message_id'] == 'test_message_id'
    
    def test_get_email_content_with_parts(self, gmail_service):
        """Test email content retrieval with multipart message"""
        mock_service = Mock()
        gmail_service.service = mock_service
        
        # Mock multipart message
        mock_message = {
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Multipart Test'}
                ],
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': 'UGxhaW4gdGV4dCBib2R5'  # "Plain text body"
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': 'PGh0bWw+SFRNTCBib2R5PC9odG1sPg=='  # "<html>HTML body</html>"
                        }
                    }
                ]
            }
        }
        
        mock_get = Mock()
        mock_service.users.return_value.messages.return_value.get.return_value = mock_get
        mock_get.execute.return_value = mock_message
        
        result = gmail_service.get_email_content('multipart_test')
        
        assert result is not None
        assert result['subject'] == 'Multipart Test'
        assert 'Plain text body' in result['body'] or '<html>HTML body</html>' in result['body']
    
    def test_get_email_content_exception(self, gmail_service):
        """Test email content retrieval with exception"""
        mock_service = Mock()
        gmail_service.service = mock_service
        
        # Mock exception
        mock_service.users.return_value.messages.return_value.get.side_effect = Exception("API Error")
        
        result = gmail_service.get_email_content('error_test')
        
        assert result is None
    
    @patch('services.gmail_service.EnrichmentService')
    def test_run_ingestion_success(self, mock_enrichment, app, gmail_service):
        """Test successful ingestion run"""
        with app.app_context():
            # Setup mocks
            with patch.object(gmail_service, 'get_idealista_emails') as mock_get_emails:
                mock_get_emails.return_value = [
                    {
                        'source_email_id': 'test_email_1',
                        'title': 'Test Property',
                        'price': 150000.0,
                        'area': 1500.0,
                        'municipality': 'Valencia',
                        'land_type': 'developed',
                        'description': 'Nice property',
                        'legal_status': 'Developed'
                    }
                ]
                
                # Mock enrichment service
                mock_enrichment_instance = Mock()
                mock_enrichment.return_value = mock_enrichment_instance
                mock_enrichment_instance.enrich_land.return_value = True
                
                result = gmail_service.run_ingestion()
                
                assert result == 1
                
                # Verify land was created
                land = Land.query.filter_by(source_email_id='test_email_1').first()
                assert land is not None
                assert land.title == 'Test Property'
                assert land.price == 150000.0
    
    def test_run_ingestion_no_emails(self, app, gmail_service):
        """Test ingestion run with no emails"""
        with app.app_context():
            with patch.object(gmail_service, 'get_idealista_emails') as mock_get_emails:
                mock_get_emails.return_value = []
                
                result = gmail_service.run_ingestion()
                
                assert result == 0
    
    @patch('services.gmail_service.EnrichmentService')
    def test_run_ingestion_duplicate_email(self, mock_enrichment, app, gmail_service):
        """Test ingestion with duplicate email (should skip)"""
        with app.app_context():
            # Create existing land
            existing_land = Land(
                source_email_id='duplicate_email',
                title='Existing Land'
            )
            db.session.add(existing_land)
            db.session.commit()
            
            # Setup mock to return same email ID
            with patch.object(gmail_service, 'get_idealista_emails') as mock_get_emails:
                mock_get_emails.return_value = [
                    {
                        'source_email_id': 'duplicate_email',
                        'title': 'Duplicate Property',
                        'land_type': 'developed'
                    }
                ]
                
                result = gmail_service.run_ingestion()
                
                assert result == 0  # Should not process duplicate
                
                # Verify original land still exists unchanged
                land = Land.query.filter_by(source_email_id='duplicate_email').first()
                assert land.title == 'Existing Land'
    
    def test_run_ingestion_exception(self, app, gmail_service):
        """Test ingestion run with exception"""
        with app.app_context():
            with patch.object(gmail_service, 'get_idealista_emails') as mock_get_emails:
                mock_get_emails.side_effect = Exception("Gmail API Error")
                
                result = gmail_service.run_ingestion()
                
                assert result == 0
