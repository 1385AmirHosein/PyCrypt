import sys
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from traceback import format_exception, print_exception
from typing import TextIO, override

from PyQt6.QtCore import (QAbstractListModel, QModelIndex, QMutex, QObject, Qt, QThread, QWaitCondition, pyqtSignal,
                          pyqtSlot)
from PyQt6.QtGui import QCloseEvent, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase, QPalette
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox

import resources
from exclusion_ui import Ui_frmExclusion as ExclusionUI
from files_cipher import CipherEngine, Files
from pycrypt_ui import Ui_PyCrypt as MainUI
from qss import style


def crash_handler(exc_type, exc_value, exc_traceback) -> None:
    if sys.stderr:
        print_exception(exc_type, exc_value, exc_traceback)
        sys.stderr.flush()
    try:
        with open("crash log.txt", 'a', encoding = "utf-8") as log:
            log.write(f"[{datetime.now().strftime('%H:%M:%S')}] program crashed!\n")
            log.write("".join(format_exception(exc_type, exc_value, exc_traceback)))
    except Exception as e:
        if sys.stdout:
            print(str(e))
    sys.exit(1)


def set_style(app: QApplication) -> None:
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1f22"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6e6e6"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#2b2d31"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#232427"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6e6e6"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2b2d31"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6e6e6"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4a90e2"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2b2d31"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e6e6e6"))
    app.setPalette(palette)
    app.setStyleSheet(style)


class FileListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.files: list[tuple[str, str]] = []
        self.file_index: dict[str, int] = {}

    @override
    def rowCount(self, parent: QModelIndex) -> int:
        return len(self.files)

    @override
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QColor | str | None:
        if not index.isValid() or not (0 <= index.row() < len(self.files)):
            return None
        path, status = self.files[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return path
        if role == Qt.ItemDataRole.ToolTipRole:
            return path
        if role == Qt.ItemDataRole.BackgroundRole:
            if status == "success":
                return QColor(0x2e7d32)
            elif status == "failed":
                return QColor(0xc62828)
            elif status == "excluded":
                return QColor(0x1565c0)
        if role == Qt.ItemDataRole.ForegroundRole and status:
            return QColor(Qt.GlobalColor.white)
        return None

    def add_paths(self, paths: list[str]) -> None:
        if not paths:
            return
        start_row = len(self.files)
        end_row = start_row + len(paths) - 1
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        for path in paths:
            self.file_index[path] = len(self.files)
            self.files.append((path, ''))
        self.endInsertRows()

    def set_status(self, path: str, status: str) -> None:
        if (row := self.file_index.get(path)) is None:
            return
        self.files[row] = (path, status)
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.BackgroundRole])

    def remove(self, indices: list[int]) -> None:
        indices.sort(reverse = True)
        for idx in indices:
            self.beginRemoveRows(QModelIndex(), idx, idx)
            del self.files[idx]
            self.endRemoveRows()
        self.file_index = {path: i for i, (path, _) in enumerate(self.files)}

    def clear(self) -> None:
        self.beginResetModel()
        self.files.clear()
        self.file_index.clear()
        self.endResetModel()


class FileScanner(QObject):
    files_found: pyqtSignal = pyqtSignal(list)
    exception: pyqtSignal = pyqtSignal(Exception)
    finished: pyqtSignal = pyqtSignal()

    def __init__(self, files: Files, paths: list[str]) -> None:
        super().__init__()
        self.files: Files = files
        self.paths: list[str] = paths
        self.cancel_requested: bool = False

    @pyqtSlot()
    def scan_files(self) -> None:
        try:
            files: list[str] = []
            for path in self.paths:
                if not path:
                    continue
                for file in self.files(path):
                    if self.cancel_requested:
                        self.finished.emit()
                        return
                    files.append(file)
                    if len(files) >= 1000:
                        self.files_found.emit(files)
                        files = []
            self.files_found.emit(files)
            self.finished.emit()
        except Exception as e:
            self.exception.emit(e)


class CryptoWorker(QObject):
    progress: pyqtSignal = pyqtSignal(int)
    file_finish: pyqtSignal = pyqtSignal(Path, str)
    write_log: pyqtSignal = pyqtSignal(str)
    error: pyqtSignal = pyqtSignal(Path, Exception)
    finished: pyqtSignal = pyqtSignal()
    exception: pyqtSignal = pyqtSignal(Exception)

    class StopOperation(Exception):
        pass

    def __init__(self, files: Iterator[tuple[Path, int, bool]], operation:
    Callable[[Path, int, Callable[[int], None], bool], None], size: int, temp: bool) -> None:
        super().__init__()
        self.files = files
        self.cryptor = operation
        self.total_size = size if size > 0 else 1
        self.temp = temp
        self.byte_progressed: int = 0
        self.current_file_progressed: int = 0
        self.last_emitted_percent: int = 0
        self.ignore_errors: bool = False
        self._mutex: QMutex = QMutex()
        self._condition: QWaitCondition = QWaitCondition()
        self._pending_file: tuple[Path, int] | None = None
        self._is_pause: bool = False
        self._is_stopped: bool = False
        self._safe_stop: bool = False

    @pyqtSlot()
    def start(self) -> None:
        self.write_log.emit("Operation Started")
        self._crypt_files()

    def pause(self) -> bool:
        self._mutex.lock()
        self._is_pause = not self._is_pause
        if not self._is_pause:
            self._condition.wakeAll()
        self.write_log.emit('pause' if self._is_pause else 'resume')
        is_pause: bool = self._is_pause
        self._mutex.unlock()
        return is_pause

    def stop(self, *, safe: bool = False) -> None:
        self._mutex.lock()
        self._is_pause = False
        if safe:
            self._safe_stop = True
        else:
            self._is_stopped = True
        self.write_log.emit('safe-stop' if safe else 'force-stop')
        self._condition.wakeAll()
        self._mutex.unlock()

    @pyqtSlot(str)
    def handle_error(self, action: str) -> None:
        if self._pending_file is None:
            return
        file = self._pending_file[0]
        if action == "retry":
            self.byte_progressed -= self.current_file_progressed
            if (percent := min(100, int((self.byte_progressed / self.total_size) * 100))) < self.last_emitted_percent:
                self.last_emitted_percent = percent
                self.progress.emit(percent)
            self._crypt_files()
        elif action == "skip":
            self._skip()
            self._crypt_files()
        else:
            self.file_finish.emit(file, "failed")
            self.finished.emit()
            return

    def _crypt_files(self) -> None:
        while True:
            if self._is_stopped or self._safe_stop:
                self.finished.emit()
                return
            try:
                if self._pending_file is None:
                    try:
                        file, size, included = next(self.files)
                        self._pending_file = file, size
                        if not included:
                            self.write_log.emit(f"EXCLUDED: {file!s}")
                            self.file_finish.emit(file, "excluded")
                            self._pending_file = None
                            continue
                    except StopIteration:
                        self.finished.emit()
                        return
                try:
                    self.current_file_progressed = 0
                    self._send_percent(0)
                    self.cryptor(*self._pending_file, self._send_percent, self.temp)
                    self.file_finish.emit(self._pending_file[0], "success")
                    self._pending_file = None
                    if self._safe_stop:
                        self.finished.emit()
                        return
                except self.StopOperation:
                    file = self._pending_file[0]
                    if not self.temp and self._is_stopped and self.current_file_progressed > 0:
                        file.replace(file.with_stem(f"{file.stem}-CORRUPTED"))
                    self.file_finish.emit(file, "failed")
                    self.finished.emit()
                    return
                except Exception as e:
                    file = self._pending_file[0]
                    self.write_log.emit(f"FAILED: {file!s} ({type(e).__name__}): {e!s}")
                    if self.ignore_errors:
                        self._skip()
                        continue
                    self.error.emit(file, e)
                    return
            except Exception as e:
                self.exception.emit(e)
                return

    def _send_percent(self, byte_size) -> None:
        if self._is_stopped:
            raise self.StopOperation("Operation stopped!")
        self._mutex.lock()
        while self._is_pause:
            self._condition.wait(self._mutex)
        self._mutex.unlock()
        if self._is_stopped:
            raise self.StopOperation("Operation stopped!")
        self.byte_progressed += byte_size
        self.current_file_progressed += byte_size
        if (percent := min(100, int((self.byte_progressed / self.total_size) * 100))) > self.last_emitted_percent:
            self.last_emitted_percent = percent
            self.progress.emit(percent)

    def _skip(self) -> None:
        if (file := self._pending_file) is None:
            return
        remaining_bytes: int = file[1] - self.current_file_progressed
        self.byte_progressed += remaining_bytes
        if (percent := min(100, int((self.byte_progressed / self.total_size) * 100))) > self.last_emitted_percent:
            self.last_emitted_percent = percent
            self.progress.emit(percent)
        self.file_finish.emit(file[0], "failed")
        self._pending_file = None


class FrmExclusion(QDialog):
    def __init__(self, files: Files, parent: QMainWindow) -> None:
        super().__init__(parent)
        self.ui = ExclusionUI()
        self.ui.setupUi(self)
        self.setFixedSize(self.size())
        self.files = files
        self.ui.lstExclusion.addItems(self.files.get_exclusions())
        self.ui.btnClearExclusion.setEnabled(bool(self.ui.lstExclusion.count()))
        self.connect_signals()

    def connect_signals(self) -> None:
        update_btn_text = lambda: self.ui.btnAddExclusion.setText(
            "افزودن" if self.ui.cmbExclusion.currentIndex() == 2 or self.ui.txtExclusion.text() else "جستجو")
        self.ui.cmbExclusion.currentIndexChanged.connect(update_btn_text)
        self.ui.btnAddExclusion.clicked.connect(self.on_btn_add_exclusion_clicked)
        self.ui.btnClearExclusion.clicked.connect(self.on_btn_clear_exclusion_clicked)
        self.ui.btnDeleteExclusion.clicked.connect(self.on_btn_delete_exclusion_clicked)
        self.ui.txtExclusion.textChanged.connect(update_btn_text)
        self.ui.lstExclusion.itemSelectionChanged.connect(lambda: self.ui.btnDeleteExclusion.setEnabled(bool(
            self.ui.lstExclusion.selectedItems())))

    def on_btn_add_exclusion_clicked(self) -> None:
        exclude: list[str]
        if self.ui.cmbExclusion.currentIndex() == 0:
            if self.ui.txtExclusion.text():
                exclude = [str(Path(self.ui.txtExclusion.text()).resolve())]
            else:
                exclude = \
                    QFileDialog.getOpenFileNames(self, "فایل های مورد نظر را انتخاب کنید", filter = "All File (*)")[0]
            if not exclude:
                return
            self.files.add_exclusion(exclude)
        elif self.ui.cmbExclusion.currentIndex() == 1:
            if self.ui.txtExclusion.text():
                exclude = [str(Path(self.ui.txtExclusion.text()).resolve())]
            else:
                exclude = [QFileDialog.getExistingDirectory(self, "پوشه مورد نظر را انتخاب کنید")]
            if not exclude[0]:
                return
            self.files.add_exclusion(exclude, folder = True)
        else:
            if not self.ui.txtExclusion.text().strip():
                QMessageBox.critical(self, "خطا", "پسوند فایل مورد نظر را در تکست باکس بنویسید")
                return
            self.files.add_exclusion([self.ui.txtExclusion.text()], suffix = True)
        self.ui.lstExclusion.clear()
        self.ui.lstExclusion.addItems(self.files.get_exclusions())
        self.ui.txtExclusion.clear()
        self.ui.btnClearExclusion.setEnabled(bool(self.ui.lstExclusion.count()))

    def on_btn_clear_exclusion_clicked(self) -> None:
        self.ui.lstExclusion.clear()
        self.files.clear_exclusion()
        self.ui.btnClearExclusion.setEnabled(False)

    def on_btn_delete_exclusion_clicked(self) -> None:
        self.files.remove_exclusion([item.text() for item in self.ui.lstExclusion.selectedItems()])
        self.ui.lstExclusion.clear()
        self.ui.lstExclusion.addItems(self.files.get_exclusions())
        self.ui.btnClearExclusion.setEnabled(bool(self.ui.lstExclusion.count()))


class MainWindow(QMainWindow):
    crypto_action: pyqtSignal = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.ui: MainUI = MainUI()
        self.ui.setupUi(self)
        self.list_model = FileListModel()
        self.init_ui()
        self.connect_signals()
        self.files: Files = Files()
        self.cipher_engine: CipherEngine = CipherEngine()
        self.log: TextIO | None = None
        self.scan_thread: QThread | None = None
        self.scanner: FileScanner | None = None
        self.crypt_thread: QThread | None = None
        self.crypto_worker: CryptoWorker | None = None

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        data = event.mimeData()
        if not data.hasUrls():
            event.ignore()
            return
        file = [f for url in data.urls() if (f := url.toLocalFile())]
        if not file:
            event.ignore()
            return
        event.acceptProposedAction()
        self.scan_file(file)

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.crypto_worker:
            QMessageBox.critical(self, "خطا", "اول عملیات را کامل متوقف کنید")
            event.ignore()
            return
        elif self.scan_thread and self.scanner:
            self.scanner.cancel_requested = True
            self.scan_thread.quit()
            self.scan_thread.wait(5000)
        if self.log:
            self.write_log("Session ended")
            self.log.close()
        event.accept()

    def init_ui(self) -> None:
        self.setFixedSize(self.size())
        self.ui.txtPath.setClearButtonEnabled(True)
        self.ui.txtKeyPass.setClearButtonEnabled(True)
        self.ui.txtLog.setClearButtonEnabled(True)
        self.ui.lstFiles.setUniformItemSizes(True)
        self.ui.lstFiles.setModel(self.list_model)
        self.ui.lstFiles.setSpacing(1)
        self.ui.prgRemaining.hide()
        self.ui.lcdRemaining.hide()
        self.ui.lblRemaining.hide()

    def connect_signals(self) -> None:
        self.ui.btnFile.clicked.connect(self.on_btn_file_clicked)
        self.ui.btnKeyPass.clicked.connect(self.on_btn_keypass_clicked)
        self.ui.btnCipher.clicked.connect(self.on_btn_cipher_clicked)
        self.ui.btnGenKeyPass.clicked.connect(self.on_btn_genkeypass_clicked)
        self.ui.btnDeleteAll.clicked.connect(self.on_btn_deleteall_clicked)
        self.ui.btnDelete.clicked.connect(self.on_btn_delete_clicked)
        self.ui.btnExclusion.clicked.connect(self.on_btn_exclusion_clicked)
        self.ui.btnLog.clicked.connect(self.on_btn_log_clicked)
        self.ui.rdoFiles.toggled.connect(lambda: self.ui.lblPath.setText("آدرس فایل:"))
        self.ui.rdoFolder.toggled.connect(lambda: self.ui.lblPath.setText("آدرس پوشه:"))
        self.ui.rdoKey.toggled.connect(self.on_rdo_key_toggled)
        self.ui.rdoPass.toggled.connect(self.on_rdo_pass_toggled)
        self.ui.rdoEncrypt.toggled.connect(self.on_rdo_encrypt_decrypt_toggled)
        self.ui.rdoDecrypt.toggled.connect(self.on_rdo_encrypt_decrypt_toggled)
        self.ui.chkLog.toggled.connect(self.on_chk_log_toggled)
        self.ui.txtPath.textChanged.connect(lambda: self.ui.btnFile.setText("ثبت" if self.ui.txtPath.text()
                                                                            else "جستجو"))
        self.ui.txtKeyPass.textChanged.connect(lambda: self.ui.btnKeyPass.setText(
            "ثبت" if self.ui.txtKeyPass.text() else "جستجو") if self.ui.rdoKey.isChecked() else None)
        self.ui.txtLog.textChanged.connect(lambda: self.ui.btnLog.setText("ثبت" if self.ui.txtLog.text() else "جستجو"))
        self.ui.lstFiles.selectionModel().selectionChanged.connect(lambda: self.ui.btnDelete.setEnabled(bool(
            self.ui.lstFiles.selectedIndexes())))

    def on_btn_file_clicked(self) -> None:
        if file := self.ui.txtPath.text():
            file = file.strip().strip('"')
            if Path(file).exists():
                self.scan_file([file])
                self.ui.txtPath.clear()
            else:
                QMessageBox.critical(self, "خطا", "فایل یا پوشه وجود ندارد")
        else:
            if self.ui.rdoFiles.isChecked():
                self.scan_file(QFileDialog.getOpenFileNames(self, "فایل های مورد نظر را انتخاب کنید")[0])
            else:
                self.scan_file([QFileDialog.getExistingDirectory(self, "پوشه مورد نظر را انتخاب کنید")])

    def on_btn_keypass_clicked(self) -> None:
        if self.ui.rdoKey.isChecked():
            key: str
            if self.ui.txtKeyPass.text():
                if self.ui.txtKeyPass.text()[-4:].lower() != ".bin":
                    QMessageBox.critical(self, "خطا", "پسوند فایل اشتباه است")
                    return
                key = self.ui.txtKeyPass.text()
            else:
                if not (key := QFileDialog.getOpenFileName(self, "کلید خود را انتخاب کنید",
                                                           filter = "Key File (*.bin)")[0]):
                    return
            try:
                with open(key, "rb") as key_file:
                    self.cipher_engine.set_key(key_file.read(2048))
                self.files.add_exclusion([key])
                QMessageBox.information(self, "موفقیت", "کلید با موفقیت ثبت شد")
                self.ui.txtKeyPass.setText(str(Path(key)))
                self.ui.btnKeyPass.setText("\u2705")
            except ValueError:
                QMessageBox.critical(self, "خطا", "مقدار کلید نامعتبر است")
            except FileNotFoundError:
                QMessageBox.critical(self, "خطا", "کلید پیدا نشد")
            except PermissionError:
                QMessageBox.critical(self, "خطا", "دسترسی رد شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", str(e))
        else:
            if self.ui.txtKeyPass.echoMode() == self.ui.txtKeyPass.EchoMode.Password:
                self.ui.btnKeyPass.setText("مخفی")
                self.ui.txtKeyPass.setEchoMode(self.ui.txtKeyPass.EchoMode.Normal)
            else:
                self.ui.btnKeyPass.setText("نمایش")
                self.ui.txtKeyPass.setEchoMode(self.ui.txtKeyPass.EchoMode.Password)

    def on_btn_cipher_clicked(self) -> None:
        if self.crypto_worker is not None:
            if self.crypto_worker.pause():
                self.ui.btnCipher.setText("ادامه \u25b6\ufe0f")
                self.ui.btnCipher.setToolTip("از سرگیری عملیات")
            else:
                self.ui.btnCipher.setText("مکث \u23f8\ufe0f")
                self.ui.btnCipher.setToolTip("توقف موقت عملیات")
            return
        if not self.files:
            QMessageBox.critical(self, "خطا", "هیچ فایلی برای انجام عملیات نیست")
            return
        if self.ui.rdoPass.isChecked():
            if self.ui.txtKeyPass.text():
                self.cipher_engine.set_password(self.ui.txtKeyPass.text())
            else:
                QMessageBox.critical(self, "خطا", "پسورد نمیتواند خالی باشد")
                return
        if not self.cipher_engine.is_key_set:
            QMessageBox.critical(self, "خطا", "کلید تنظیم نشده است")
            return
        if not self.ui.chkTempFile.isChecked():
            txt: str = "استفاده از فایل موقت برای انجام عملیات غیرفعال شده است" \
                       "\nدرصورت بروز خطا فایل های شما غیر قابل بازگشت خواهد بود!!!" \
                       "\nآیا مایل به فعال سازی آن هستید؟"
            mbox: QMessageBox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Icon.Warning)
            mbox.setText(txt)
            mbox.setWindowTitle("هشدار")
            yes = mbox.addButton("بله", QMessageBox.ButtonRole.YesRole)
            no = mbox.addButton("خیر", QMessageBox.ButtonRole.NoRole)
            mbox.addButton("لغو", QMessageBox.ButtonRole.RejectRole)
            mbox.exec()
            if mbox.clickedButton() == yes:
                self.ui.chkTempFile.setChecked(True)
            elif mbox.clickedButton() == no:
                if self.ui.rdoDecrypt.isChecked():
                    txt = "رمزگشایی بدون استفاده از فایل موقت در صورت رمز اشتباه نابودی کامل فایل را در پی خواهد داشت" \
                          "\nآیا مایل به فعال سازی آن هستید؟"
                    mbox.setText(txt)
                    mbox.exec()
                    if mbox.clickedButton() == yes:
                        self.ui.chkTempFile.setChecked(True)
                    elif mbox.clickedButton() == no:
                        pass
                    else:
                        return
            else:
                return
        self.start_operation()

    def on_btn_genkeypass_clicked(self) -> None:
        if self.crypto_worker is not None:
            mbox: QMessageBox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Icon.Warning)
            mbox.setText("آیا عملیات را قطع میکنید؟")
            mbox.setWindowTitle("هشدار")
            yes = mbox.addButton("همین الان", QMessageBox.ButtonRole.YesRole)
            accept = mbox.addButton("بعد این فایل", QMessageBox.ButtonRole.AcceptRole)
            mbox.addButton("انصراف", QMessageBox.ButtonRole.RejectRole)
            mbox.exec()
            if self.crypto_worker is None:
                return
            if mbox.clickedButton() == yes:
                if not self.ui.chkTempFile.isChecked():
                    txt: str = "استفاده از فایل موقت برای انجام عملیات غیرفعال شده است\n" \
                               "درصورت لغو همین الان فایل جاری شما نابود خواهد شد\nآیا عملیات را قطع میکنید؟"
                    mbox.setText(txt)
                    mbox.exec()
                    if self.crypto_worker is None:
                        return
                    if mbox.clickedButton() == yes:
                        pass
                    elif mbox.clickedButton() == accept:
                        self.crypto_worker.stop(safe = True)
                        return
                    else:
                        return
                self.crypto_worker.stop()
                return
            elif mbox.clickedButton() == accept:
                self.crypto_worker.stop(safe = True)
                return
            else:
                return
        if self.ui.rdoKey.isChecked():
            key: str
            if path := self.ui.txtKeyPass.text():
                if path[-4:].lower() != ".bin":
                    QMessageBox.critical(self, "خطا", "پسوند فایل نامعتبر است")
                    return
                elif Path(path).exists():
                    QMessageBox.critical(self, "خطا", "فایل کلید از قبل وجود دارد")
                    return
                key = path
            elif not (key := QFileDialog.getSaveFileName(
                    self, "محل ذخیره کلید را انتخاب کنید", filter = "Key File (*.bin)")[0]):
                return
            try:
                with open(key, "wb") as key_file:
                    generated_key: bytes = self.cipher_engine.generate_key()
                    key_file.write(generated_key)
                    self.cipher_engine.set_key(generated_key)
                self.files.add_exclusion([key])
                QMessageBox.information(self, "موفقیت", "کلید با موفقیت ساخته شد")
                self.ui.txtKeyPass.setText(str(Path(key)))
                self.ui.btnKeyPass.setText("\u2705")
            except PermissionError:
                QMessageBox.critical(self, "خطا", "دسترسی رد شد")
            except Exception as e:
                QMessageBox.critical(self, "خطا", str(e))
        else:
            self.ui.txtKeyPass.setText(self.cipher_engine.generate_password())

    def on_btn_deleteall_clicked(self) -> None:
        self.list_model.clear()
        self.files.clear()
        self.ui.lcdRemaining.display(0)
        self.ui.btnDeleteAll.setEnabled(False)

    def on_btn_delete_clicked(self) -> None:
        if self.crypt_thread:
            QMessageBox.critical(self, "خطا", "تا پایان عملیات صبر کنید")
            return
        indices: list[int] = []
        for path in self.ui.lstFiles.selectedIndexes():
            indices.append(path.row())
            self.files.remove_file(path.data())
        self.list_model.remove(indices)
        self.ui.lstFiles.clearSelection()
        self.ui.lcdRemaining.display(len(self.files))
        self.ui.btnDeleteAll.setEnabled(bool(self.files))

    def on_btn_exclusion_clicked(self) -> None:
        dialog = FrmExclusion(self.files, self)
        dialog.exec()
        dialog.deleteLater()
        self.ui.lcdRemaining.display(len(self.files))

    def on_btn_log_clicked(self) -> None:
        log_file: str | Path
        if log_file := self.ui.txtLog.text():
            if log_file[-4:].lower() != ".txt":
                QMessageBox.critical(self, "خطا", "پسوند فایل باید txt باشد")
                return
        elif not (log_file := QFileDialog.getSaveFileName(self, "محل ذخیره فایل گزارش را انتخاب کنید", f"{
        datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.txt", filter = "Text File (*.txt)")[0]):
            return
        log_file = Path(log_file).resolve()
        if self.log:
            self.log.close()
            self.log = None
        try:
            self.log = open(log_file, "a", 1, 'utf-8')
            self.files.add_exclusion([str(log_file)])
            self.log.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] New session\n")
            self.ui.txtLog.setText(str(log_file))
            self.ui.btnLog.setText("\u2705")
        except PermissionError:
            QMessageBox.critical(self, "خطا", "دسترسی رد شد")
        except FileNotFoundError:
            QMessageBox.critical(self, "خطا", "آدرس فایل اشتباه است")
        except Exception as e:
            QMessageBox.critical(self, "خطا", str(e))

    def on_rdo_key_toggled(self) -> None:
        self.ui.lblKeyPass.setText("آدرس کلید:")
        self.ui.btnKeyPass.setText("جستجو")
        self.ui.btnGenKeyPass.setText("ساخت کلید")
        self.ui.btnGenKeyPass.setToolTip("ساخت یک کلید 32 بایتی")
        self.ui.txtKeyPass.setEchoMode(self.ui.txtKeyPass.EchoMode.Normal)
        self.ui.txtKeyPass.clear()
        self.cipher_engine.clear_key()

    def on_rdo_pass_toggled(self) -> None:
        self.ui.lblKeyPass.setText("پسورد:")
        self.ui.btnKeyPass.setText("نمایش")
        self.ui.btnGenKeyPass.setText("ساخت پسورد")
        self.ui.btnGenKeyPass.setToolTip(f"ساخت یک پسورد {self.cipher_engine.PASSWORD_SIZE} کاراکتری")
        self.ui.txtKeyPass.setEchoMode(self.ui.txtKeyPass.EchoMode.Password)
        self.ui.txtKeyPass.clear()
        self.cipher_engine.clear_key()

    def on_rdo_encrypt_decrypt_toggled(self) -> None:
        if self.ui.rdoEncrypt.isChecked():
            self.ui.btnCipher.setText("رمزگذاری")
            self.ui.btnCipher.setToolTip("شروع عملیات رمزگذاری")
        else:
            self.ui.btnCipher.setText("رمزگشایی")
            self.ui.btnCipher.setToolTip("شروع عملیات رمزگشایی")

    def on_chk_log_toggled(self) -> None:
        if self.ui.chkLog.isChecked():
            self.ui.lblLog.setEnabled(True)
            self.ui.txtLog.setEnabled(True)
            self.ui.btnLog.setEnabled(True)
        else:
            self.ui.lblLog.setEnabled(False)
            self.ui.txtLog.setEnabled(False)
            self.ui.btnLog.setEnabled(False)
            self.ui.txtLog.clear()
            if self.log:
                self.write_log("Session ended")
                self.log.close()
                self.log = None

    def set_busy(self, busy: bool) -> None:
        self.setAcceptDrops(not busy)
        self.ui.grpFile.setEnabled(not busy)
        self.ui.grpKeyPass.setEnabled(not busy)
        self.ui.grpCipher.setEnabled(not busy)
        self.ui.chkLog.setEnabled(not busy)
        self.ui.chkTempFile.setEnabled(not busy)
        self.ui.txtPath.setEnabled(not busy)
        self.ui.txtKeyPass.setEnabled(not busy)
        self.ui.txtLog.setEnabled(not busy and self.ui.chkLog.isChecked())
        self.ui.btnFile.setEnabled(not busy)
        self.ui.btnKeyPass.setEnabled(not busy)
        self.ui.btnDeleteAll.setEnabled(not busy)
        self.ui.btnExclusion.setEnabled(not busy)
        self.ui.btnLog.setEnabled(not busy and self.ui.chkLog.isChecked())

    def scan_file(self, file: list[str]) -> None:
        if not (file and file[0]):
            return
        self.ui.prgRemaining.setRange(0, 0)
        self.ui.prgRemaining.setTextVisible(False)
        self.ui.prgRemaining.show()
        self.ui.lcdRemaining.show()
        self.ui.lblRemaining.show()
        self.scan_thread = QThread(self)
        self.scanner = FileScanner(self.files, file)
        self.scanner.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scanner.scan_files)
        self.scanner.files_found.connect(self.on_files_found)
        self.scanner.exception.connect(self.on_exception_thread)
        self.scanner.finished.connect(self.scan_thread.quit)
        self.scanner.finished.connect(self.scanner.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()
        self.ui.btnFile.setEnabled(False)
        self.ui.btnCipher.setEnabled(False)
        self.ui.btnDeleteAll.setEnabled(False)
        self.ui.btnExclusion.setEnabled(False)
        self.setAcceptDrops(False)

    @pyqtSlot(list)
    def on_files_found(self, files: list[str]) -> None:
        self.list_model.add_paths(files)
        self.ui.lcdRemaining.display(len(self.files))

    @pyqtSlot()
    def on_scan_finished(self) -> None:
        self.scan_thread = self.scanner = None
        self.ui.prgRemaining.setRange(0, 100)
        self.ui.prgRemaining.setTextVisible(True)
        self.ui.btnDeleteAll.setEnabled(bool(self.files))
        self.ui.btnFile.setEnabled(True)
        self.ui.btnCipher.setEnabled(True)
        self.ui.btnExclusion.setEnabled(True)
        self.setAcceptDrops(True)
        if failed_files := self.files.failed_to_add:
            mbox: QMessageBox = QMessageBox(self)
            mbox.setIcon(QMessageBox.Icon.Critical)
            mbox.setWindowTitle("خطا")
            mbox.setText(f"{len(failed_files)} فایل اضافه نشد")
            mbox.setDetailedText('\n'.join(failed_files))
            mbox.exec()
            self.files.failed_to_add.clear()

    def start_operation(self) -> None:
        if self.ui.chkLog.isChecked() and self.log is None:
            QMessageBox.critical(self, "خطا", "گزارش فعال شده ولی فایلی را برای ثبت گزارش انتخاب نکردید")
            return
        if self.log:
            self.log.write(f"Operation: {'Encrypt' if self.ui.rdoEncrypt.isChecked() else 'Decrypt'} {'with Temp File'
            if self.ui.chkTempFile.isChecked() else 'without Temp File'}\n")
            self.log.write(f"{'Password-Based' if self.ui.rdoPass.isChecked() else 'Key File-Based'}\n")
        operation = self.cipher_engine.encrypt if self.ui.rdoEncrypt.isChecked() else self.cipher_engine.decrypt
        self.ui.prgRemaining.setValue(0)
        self.ui.lcdRemaining.display(len(self.files))
        self.ui.btnCipher.setText("مکث \u23f8\ufe0f")
        self.ui.btnCipher.setToolTip("توقف موقت عملیات")
        self.ui.btnGenKeyPass.setText("توقف \u23f9\ufe0f")
        self.ui.btnGenKeyPass.setToolTip("توقف کامل عملیات")
        self.set_busy(True)
        self.crypt_thread = QThread(self)
        self.crypto_worker = CryptoWorker(iter(self.files), operation, self.files.size, self.ui.chkTempFile.isChecked())
        self.crypto_worker.moveToThread(self.crypt_thread)
        self.crypt_thread.started.connect(self.crypto_worker.start)
        self.crypto_worker.progress.connect(self.ui.prgRemaining.setValue)
        self.crypto_worker.file_finish.connect(self.file_crypted)
        self.crypto_worker.write_log.connect(self.write_log)
        self.crypto_action.connect(self.crypto_worker.handle_error)
        self.crypto_worker.error.connect(self.show_error)
        self.crypto_worker.exception.connect(self.on_exception_thread)
        self.crypto_worker.finished.connect(self.crypt_thread.quit)
        self.crypto_worker.finished.connect(self.crypto_worker.deleteLater)
        self.crypt_thread.finished.connect(self.crypt_thread.deleteLater)
        self.crypt_thread.finished.connect(self.on_operation_finished)
        self.crypt_thread.start()

    @pyqtSlot(Path, Exception)
    def show_error(self, file: Path, exc: Exception) -> None:
        error_text: str
        if type(exc) is self.cipher_engine.DecryptionFailed:
            error_text = "رمز عبور اشتباه است یا فایل دستکاری شده است"
        elif type(exc) is self.cipher_engine.NotEncrypted:
            error_text = "فایل رمزنگاری نشده"
        elif type(exc) is self.cipher_engine.FileTooBig:
            error_text = "فایل از 64 گیگ بزرگتر است"
        elif type(exc) is FileNotFoundError:
            error_text = "فایل وجود ندارد"
        elif type(exc) is PermissionError:
            error_text = "دسترسی رد شد"
        else:
            error_text = str(type(exc)) + ": " + str(exc)
        mbox: QMessageBox = QMessageBox(self)
        mbox.setIcon(QMessageBox.Icon.Critical)
        mbox.setText(error_text)
        mbox.setWindowTitle("خطا")
        mbox.setInformativeText(str(file))
        if self.ui.chkTempFile.isChecked() or type(exc) is not self.cipher_engine.DecryptionFailed:
            retry = mbox.addButton("تلاش مجدد", QMessageBox.ButtonRole.AcceptRole)
        else:
            retry = None
        skip = mbox.addButton("رد شدن", QMessageBox.ButtonRole.DestructiveRole)
        ignore = mbox.addButton("رد شدن تا آخر", QMessageBox.ButtonRole.NoRole)
        mbox.addButton("توقف همه", QMessageBox.ButtonRole.RejectRole)
        mbox.exec()
        if mbox.clickedButton() is retry:
            self.crypto_action.emit("retry")
        elif mbox.clickedButton() is skip:
            self.crypto_action.emit("skip")
        elif mbox.clickedButton() is ignore:
            self.crypto_worker.ignore_errors = True
            self.crypto_action.emit("skip")
        else:
            self.crypto_action.emit("cancel")

    @pyqtSlot(str)
    def write_log(self, log: str) -> None:
        if self.log:
            self.log.write(f"[{datetime.now().strftime('%H:%M:%S')}] {log}\n")

    @pyqtSlot(Path, str)
    def file_crypted(self, file: Path, status: str) -> None:
        self.list_model.set_status(str(file), status)
        if status != "excluded":
            self.ui.lcdRemaining.display(self.ui.lcdRemaining.intValue() - 1)
        if status == "success":
            self.write_log(f"SUCCESS: {file!s}")
            delta = self.cipher_engine.HEADER_SIZE if self.ui.rdoEncrypt.isChecked() else -self.cipher_engine.HEADER_SIZE
            self.files.adjust_size(file, delta)

    @pyqtSlot()
    def on_operation_finished(self) -> None:
        self.crypt_thread = self.crypto_worker = None
        self.write_log("Operation Ended")
        if self.log:
            self.log.write('-' * 50 + '\n')
        if not self.ui.lcdRemaining.intValue():
            QMessageBox.information(self, "پیغام", "عملیات به پایان رسید")
            self.ui.prgRemaining.setValue(100)
        self.on_rdo_encrypt_decrypt_toggled()
        if self.ui.rdoKey.isChecked():
            self.ui.btnGenKeyPass.setText("ساخت کلید")
            self.ui.btnGenKeyPass.setToolTip("ساخت یک کلید 32 بایتی")
        else:
            self.ui.btnGenKeyPass.setText("ساخت پسورد")
            self.ui.btnGenKeyPass.setToolTip(f"ساخت یک پسورد {self.cipher_engine.PASSWORD_SIZE} کاراکتری")
        self.set_busy(False)

    @pyqtSlot(Exception)
    def on_exception_thread(self, exc: Exception) -> None:
        crash_handler(type(exc), exc, exc.__traceback__)


if __name__ == "__main__":
    sys.excepthook = crash_handler
    app: QApplication = QApplication(sys.argv)
    QFontDatabase.addApplicationFont(":/assets/Mikhak.ttf")
    app.setFont(QFont("Mikhak", 10))
    set_style(app)
    window: QMainWindow = MainWindow()
    window.show()
    sys.exit(app.exec())
