"""
Centralized Message Manager for CNI Digital Queue Management System
Handles multilingual messages and error responses
"""

class MessageManager:
    """Centralized message management for multilingual support"""
    
    MESSAGES = {
        # Error messages
        'ticket_generation_error': {
            'fr': 'Erreur lors de la génération du ticket',
            'en': 'Error generating ticket'
        },
        'invalid_pre_enrollment_code': {
            'fr': 'Code de pré-inscription invalide',
            'en': 'Invalid pre-enrollment code'
        },
        'pre_enrollment_required': {
            'fr': 'Code de pré-inscription requis pour ce service',
            'en': 'Pre-enrollment code required for this service'
        },
        'invalid_service_type': {
            'fr': 'Type de service invalide',
            'en': 'Invalid service type'
        },
        'ticket_not_found': {
            'fr': 'Ticket non trouvé',
            'en': 'Ticket not found'
        },
        'system_error': {
            'fr': 'Erreur système',
            'en': 'System error'
        },
        'active_ticket_exists': {
            'fr': 'Vous avez déjà un ticket actif',
            'en': 'You already have an active ticket'
        },
        'authentication_required': {
            'fr': 'Authentification requise',
            'en': 'Authentication required'
        },
        'invalid_request': {
            'fr': 'Requête invalide',
            'en': 'Invalid request'
        },
        'database_error': {
            'fr': 'Erreur de base de données',
            'en': 'Database error'
        },
        
        # Success messages
        'ticket_generated': {
            'fr': 'Ticket généré avec succès',
            'en': 'Ticket generated successfully'
        },
        'queue_optimized': {
            'fr': 'File optimisée avec succès',
            'en': 'Queue optimized successfully'
        },
        'ticket_called': {
            'fr': 'Ticket appelé avec succès',
            'en': 'Ticket called successfully'
        },
        'priority_updated': {
            'fr': 'Priorité mise à jour avec succès',
            'en': 'Priority updated successfully'
        },
        'ticket_cancelled': {
            'fr': 'Ticket annulé avec succès',
            'en': 'Ticket cancelled successfully'
        },
        
        # Status messages
        'waiting': {
            'fr': 'En attente',
            'en': 'Waiting'
        },
        'in_progress': {
            'fr': 'En cours',
            'en': 'In Progress'
        },
        'completed': {
            'fr': 'Terminé',
            'en': 'Completed'
        },
        'cancelled': {
            'fr': 'Annulé',
            'en': 'Cancelled'
        },
        
        # UI Labels
        'welcome_title': {
            'fr': 'Bienvenue au Système de File Numérique CNI',
            'en': 'Welcome to CNI Digital Queue System'
        },
        'select_language': {
            'fr': 'Sélectionnez votre langue',
            'en': 'Select your language'
        },
        'continue': {
            'fr': 'Continuer',
            'en': 'Continue'
        },
        'back': {
            'fr': 'Retour',
            'en': 'Back'
        },
        'home': {
            'fr': 'Accueil',
            'en': 'Home'
        },
        'print': {
            'fr': 'Imprimer',
            'en': 'Print'
        },
        'check_status': {
            'fr': 'Vérifier le statut',
            'en': 'Check Status'
        },
        'new_ticket': {
            'fr': 'Nouveau ticket',
            'en': 'New Ticket'
        },
        
        # Service types
        'service_new_app': {
            'fr': 'Nouvelle demande',
            'en': 'New Application'
        },
        'service_renewal': {
            'fr': 'Renouvellement',
            'en': 'Renewal'
        },
        'service_collection': {
            'fr': 'Collecte',
            'en': 'Collection'
        },
        'service_correction': {
            'fr': 'Correction',
            'en': 'Correction'
        },
        'service_emergency': {
            'fr': 'Urgence',
            'en': 'Emergency'
        }
    }
    
    @classmethod
    def get_message(cls, key, language='fr', **kwargs):
        """
        Get a message in the specified language
        
        Args:
            key: Message key
            language: Language code ('fr' or 'en')
            **kwargs: Format parameters for the message
            
        Returns:
            Formatted message string
        """
        if key not in cls.MESSAGES:
            return key  # Return key if message not found
        
        message_dict = cls.MESSAGES[key]
        message = message_dict.get(language, message_dict.get('fr', key))
        
        # Format message with kwargs if provided
        try:
            return message.format(**kwargs) if kwargs else message
        except (KeyError, ValueError):
            return message
    
    @classmethod
    def get_error_response(cls, key, language='fr', status_code=400, **kwargs):
        """
        Get a standardized error response
        
        Args:
            key: Message key
            language: Language code
            status_code: HTTP status code
            **kwargs: Format parameters
            
        Returns:
            Dictionary with error response structure
        """
        message = cls.get_message(key, language, **kwargs)
        return {
            'success': False,
            'message': message,
            'error_code': key.upper(),
            'language': language
        }, status_code
    
    @classmethod
    def get_success_response(cls, key, language='fr', data=None, **kwargs):
        """
        Get a standardized success response
        
        Args:
            key: Message key
            language: Language code
            data: Additional data to include
            **kwargs: Format parameters
            
        Returns:
            Dictionary with success response structure
        """
        message = cls.get_message(key, language, **kwargs)
        response = {
            'success': True,
            'message': message,
            'language': language
        }
        
        if data:
            response['data'] = data
            
        return response
    
    @classmethod
    def get_available_languages(cls):
        """Get list of available language codes"""
        return ['fr', 'en']
    
    @classmethod
    def validate_language(cls, language):
        """Validate and normalize language code"""
        if not language or language not in cls.get_available_languages():
            return 'fr'  # Default to French
        return language

# Global instance for easy access
message_manager = MessageManager()

def get_message(key, language='fr', **kwargs):
    """Convenience function to get a message"""
    return message_manager.get_message(key, language, **kwargs)

def get_error_response(key, language='fr', status_code=400, **kwargs):
    """Convenience function to get an error response"""
    return message_manager.get_error_response(key, language, status_code, **kwargs)

def get_success_response(key, language='fr', data=None, **kwargs):
    """Convenience function to get a success response"""
    return message_manager.get_success_response(key, language, data, **kwargs)
