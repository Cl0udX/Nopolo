"""
gui/mainWindowComponents/update_mixin.py

Mixin que añade verificación de actualizaciones al arranque.
- Ejecuta el check en un hilo secundario (no bloquea la UI)
- Muestra un diálogo no intrusivo si hay nueva versión
- Ofrece descarga con barra de progreso
- Reinicia la app al completar
"""

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal, Qt, QMetaObject, Q_ARG
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QWidget, QSizePolicy,
    QMessageBox,
)
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Hilo de verificación
# ──────────────────────────────────────────────────────────────

class _UpdateCheckThread(QThread):
    """Verifica actualizaciones en segundo plano."""
    update_found  = Signal(object)   # UpdateInfo
    no_update     = Signal()
    check_error   = Signal(str)

    def run(self):
        try:
            from core.updater import check_for_updates
            info = check_for_updates()
            if info.error:
                self.check_error.emit(info.error)
            elif info.available:
                self.update_found.emit(info)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_error.emit(str(e))


# ──────────────────────────────────────────────────────────────
# Hilo de descarga e instalación
# ──────────────────────────────────────────────────────────────

class _UpdateInstallThread(QThread):
    """Descarga e instala la actualización en segundo plano."""
    progress   = Signal(int, int, str)   # (bytes, total, msg)
    finished   = Signal(bool)            # True = éxito

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info

    def run(self):
        try:
            from core.updater import download_and_install
            ok = download_and_install(
                self.update_info,
                progress_cb=self._on_progress,
            )
            self.finished.emit(ok)
        except Exception as e:
            logger.error(f"[update] Install thread error: {e}")
            self.finished.emit(False)

    def _on_progress(self, downloaded: int, total: int, msg: str):
        self.progress.emit(downloaded, total, msg)


# ──────────────────────────────────────────────────────────────
# Diálogo de actualización disponible
# ──────────────────────────────────────────────────────────────

class UpdateAvailableDialog(QDialog):
    """Diálogo que informa al usuario de una nueva versión."""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowTitle("Actualización disponible")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        title = QLabel(f"🎉 Nopolo {self.update_info.remote_version} disponible")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # Subtítulo versión actual
        subtitle = QLabel(f"Versión instalada: {self.update_info.local_version}")
        layout.addWidget(subtitle)

        # Changelog si existe
        if self.update_info.changelog:
            layout.addWidget(QLabel("Cambios:"))
            changes_text = "\n".join(f"• {c}" for c in self.update_info.changelog[:6])
            changes = QLabel(changes_text)
            changes.setWordWrap(True)
            changes.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(changes)

        layout.addSpacing(8)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_later  = QPushButton("Más tarde")
        self.btn_update = QPushButton("Actualizar ahora")
        self.btn_update.setDefault(True)
        self.btn_update.setStyleSheet(
            "QPushButton { background: #5865F2; color: white; padding: 6px 18px; border-radius: 4px; }"
            "QPushButton:hover { background: #4752C4; }"
        )

        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_update)
        layout.addLayout(btn_layout)

        self.btn_later.clicked.connect(self.reject)
        self.btn_update.clicked.connect(self.accept)


# ──────────────────────────────────────────────────────────────
# Diálogo de progreso de descarga
# ──────────────────────────────────────────────────────────────

class UpdateProgressDialog(QDialog):
    """Barra de progreso durante la descarga e instalación."""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.setWindowTitle("Actualizando Nopolo...")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._build()
        self._start()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.label = QLabel(f"Descargando Nopolo {self.update_info.remote_version}...")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        self.detail = QLabel("")
        self.detail.setStyleSheet("color: #888; font-size: 11px;")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

    def _start(self):
        self.thread = _UpdateInstallThread(self.update_info, self)
        self.thread.progress.connect(self._on_progress)
        self.thread.finished.connect(self._on_finished)
        self.thread.start()

    def _on_progress(self, downloaded: int, total: int, msg: str):
        self.detail.setText(msg)
        if total > 0:
            pct = min(int(downloaded / total * 100), 100)
            self.bar.setValue(pct)
        else:
            # Progreso indeterminado
            self.bar.setRange(0, 0)

    def _on_finished(self, success: bool):
        self.bar.setRange(0, 100)
        if success:
            self.bar.setValue(100)
            self.label.setText("✅ ¡Actualización completada!")
            self.detail.setText("La aplicación se reiniciará ahora.")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, self._restart)
        else:
            self.label.setText("❌ Error durante la actualización.")
            self.detail.setText("Revisa la consola para más detalles. Puedes actualizar manualmente.")
            # Permitir cerrar con error
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(self.accept)
            self.layout().addWidget(close_btn)

    def _restart(self):
        self.accept()
        try:
            from core.updater import restart_app
            restart_app(self.update_info)
        except Exception as e:
            logger.error(f"[update] Error al reiniciar: {e}")


# ──────────────────────────────────────────────────────────────
# Mixin principal
# ──────────────────────────────────────────────────────────────

class UpdateMixin:
    """
    Mixin para MainWindow. Añade verificación de actualizaciones al inicio.
    Llama a _schedule_update_check() desde __init__ de MainWindow.
    """

    def _schedule_update_check(self, delay_ms: int = 3000):
        """
        Programa el check de actualizaciones para unos segundos después
        de que la ventana esté completamente visible (no interfiere con el arranque).
        """
        from core.paths import get_run_mode
        if get_run_mode() != "build":
            logger.debug("[update] Modo dev — verificación de actualizaciones deshabilitada.")
            return

        from PySide6.QtCore import QTimer
        QTimer.singleShot(delay_ms, self._run_update_check)
        logger.debug(f"[update] Check programado en {delay_ms}ms.")

    def _run_update_check(self):
        """Inicia el hilo de verificación."""
        logger.info("[update] Iniciando verificación de actualizaciones...")
        self._update_check_thread = _UpdateCheckThread()
        self._update_check_thread.update_found.connect(self._on_update_found)
        self._update_check_thread.no_update.connect(
            lambda: logger.info("[update] Sin actualizaciones.")
        )
        self._update_check_thread.check_error.connect(
            lambda e: logger.warning(f"[update] Error en check: {e}")
        )
        self._update_check_thread.start()

    def _on_update_found(self, update_info):
        """Muestra el diálogo de actualización disponible."""
        logger.info(f"[update] Nueva versión: {update_info.remote_version}")
        dlg = UpdateAvailableDialog(update_info, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._start_update(update_info)

    def _start_update(self, update_info):
        """Abre el diálogo de progreso y arranca la descarga."""
        progress_dlg = UpdateProgressDialog(update_info, parent=self)
        progress_dlg.exec()
