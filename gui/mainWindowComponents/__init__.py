"""
Componentes modulares para MainWindow.
Cada mixin maneja una responsabilidad específica de la interfaz.
"""

from .ui_builder_mixin import UIBuilderMixin, ConsoleRedirector
from .table_manager_mixin import TableManagerMixin
from .effects_manager_mixin import EffectsManagerMixin
from .import_manager_mixin import ImportManagerMixin
from .provider_mixin import ProviderMixin
from .api_mixin import APIMixin
from .voice_mixin import VoiceMixin
from .playback_mixin import PlaybackMixin
from .controls_mixin import ControlsMixin
from .system_config_mixin import SystemConfigMixin
from .overlay_mixin import OverlayMixin
from .update_mixin import UpdateMixin

__all__ = [
    'ConsoleRedirector',
    'UIBuilderMixin',
    'TableManagerMixin',
    'EffectsManagerMixin',
    'ImportManagerMixin',
    'ProviderMixin',
    'APIMixin',
    'VoiceMixin',
    'PlaybackMixin',
    'ControlsMixin',
    'SystemConfigMixin',
    'OverlayMixin',
    'UpdateMixin',
]

