from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QRadioButton, QProgressBar,
                             QLineEdit, QComboBox, QListWidget, QGroupBox, QMessageBox, QCheckBox)
from PyQt6.QtGui import (QIcon, QFont, QColor, QBrush)
from PyQt6.QtCore import (Qt)
from cryptography.fernet import Fernet
import sys, os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # lblException
        self.lblException = QLabel("استثنائات : ", self)
        self.lblException.setGeometry(504, 280, 61, 21)

        # lblPassword
        self.lblPassword = QLabel("پسورد شما\nبایدفقط شامل\n10 حرف باشد", self)
        self.lblPassword.setGeometry(270, 70, 71, 61)
        self.lblPassword.hide()

        # lblPathFile
        self.lblPathFile = QLabel("آدرس پوشه : ", self)
        self.lblPathFile.setGeometry(561, 43, 71, 20)

        # lblPathKey
        self.lblPathKey = QLabel("آدرس کلید : ", self)
        self.lblPathKey.setGeometry(561, 90, 65, 20)

        # lblLog
        self.lblLog = QLabel("گزارشات", self)
        self.lblLog.setGeometry(90, 10, 61, 20)

        # lblPathLog
        self.lblPathLog = QLabel("فایل گزارشات : ", self)
        self.lblPathLog.setGeometry(570, 140, 71, 20)
        self.lblPathLog.setEnabled(False)

        # lblTypeException
        self.lblTypeException = QLabel("نوع استثناء : ", self)
        self.lblTypeException.setGeometry(580, 320, 71, 21)

        # lblTypeFileException
        self.lblTypeFileException = QLabel("نوع فایل : ", self)
        self.lblTypeFileException.setGeometry(580, 345, 71, 21)
        self.lblTypeFileException.hide()

        # btnEncrypt
        self.btnEncrypt = QPushButton("رمزگذاری", self)
        self.btnEncrypt.setIcon(QIcon(resource_path("img/lock.png")))
        self.btnEncrypt.setGeometry(501, 193, 111, 41)

        # btnDecrypt
        self.btnDecrypt = QPushButton("رمزگشایی", self)
        self.btnDecrypt.setIcon(QIcon(resource_path("img/unlock.png")))
        self.btnDecrypt.setGeometry(311, 193, 111, 41)

        # btnGenKey
        self.btnGenKey = QPushButton("ساخت کلید", self)
        self.btnGenKey.setIcon(QIcon(resource_path("img/key.png")))
        self.btnGenKey.setGeometry(691, 193, 111, 41)

        # btnBrowseFile
        self.btnBrowseFile = QPushButton("جستجو", self)
        self.btnBrowseFile.setGeometry(270, 42, 75, 25)

        # btnBrowseKey
        self.btnBrowseKey = QPushButton("جستجو", self)
        self.btnBrowseKey.setGeometry(270, 89, 75, 25)

        # btnAddException
        self.btnAddException = QPushButton("افزودن", self)
        self.btnAddException.setGeometry(580, 279, 75, 25)

        # btnBrowseLog
        self.btnBrowseLog = QPushButton("جستجو", self)
        self.btnBrowseLog.setGeometry(270, 139, 75, 25)
        self.btnBrowseLog.setEnabled(False)

        # btnAddException
        self.btnAddException = QPushButton("افزودن", self)
        self.btnAddException.setGeometry(580, 279, 75, 25)

        # txtPathFile
        self.txtPathFile = QLineEdit(self)
        self.txtPathFile.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.txtPathFile.setClearButtonEnabled(True)
        self.txtPathFile.setGeometry(351, 43, 211, 21)

        # txtPathKey
        self.txtPathKey = QLineEdit(self)
        self.txtPathKey.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.txtPathKey.setClearButtonEnabled(True)
        self.txtPathKey.setGeometry(351, 90, 211, 21)

        # txtPathLog
        self.txtPathLog = QLineEdit(self)
        self.txtPathLog.setGeometry(350, 140, 211, 21)
        self.txtPathLog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.txtPathLog.setClearButtonEnabled(True)
        self.txtPathLog.setEnabled(False)

        # txtTypeFile
        self.txtTypeFile = QLineEdit(self)
        self.txtTypeFile.setGeometry(514, 346, 69, 22)
        self.txtTypeFile.hide()

        # grpFile
        self.grpFile = QGroupBox("انتخاب فایل / پوشه", self)
        self.grpFile.setGeometry(651, 13, 191, 71)

        # grpKey
        self.grpKey = QGroupBox("انتخاب روش رمزگذاری / رمزگشایی", self)
        self.grpKey.setGeometry(651, 103, 191, 71)

        # grpLevelLog
        self.grpLevelLog = QGroupBox("سطح ثبت گزارشات", self)
        self.grpLevelLog.setGeometry(689, 280, 141, 91)
        self.grpLevelLog.setEnabled(False)

        # rdoFile
        self.rdoFile = QRadioButton("رمزگذاری / رمزگشایی فایل", self.grpFile)
        self.rdoDir = QRadioButton("رمزگذاری / رمزگشایی پوشه", self.grpFile)
        self.rdoFile.setGeometry(30, 20, 151, 21)
        self.rdoDir.setGeometry(20, 40, 161, 21)
        self.rdoDir.setChecked(True)

        # rdoKey
        self.rdoKey = QRadioButton("رمزگذاری / رمزگشایی با کلید", self.grpKey)
        self.rdoPass = QRadioButton("رمزگذاری / رمزگشایی با پسورد", self.grpKey)
        self.rdoKey.setGeometry(10, 20, 171, 21)
        self.rdoPass.setGeometry(10, 40, 171, 21)
        self.rdoKey.setChecked(True)

        # rdoSuccessLog
        self.rdoSuccessLog = QRadioButton("عملیات های موفق", self.grpLevelLog)
        self.rdoSuccessLog.setGeometry(20, 40, 111, 21)

        # rdoUnsuccessLog
        self.rdoUnsuccessLog = QRadioButton("عملیات های ناموفق", self.grpLevelLog)
        self.rdoUnsuccessLog.setGeometry(10, 60, 121, 21)

        # rdoAllLog
        self.rdoAllLog = QRadioButton("همه عملیات ها", self.grpLevelLog)
        self.rdoAllLog.setGeometry(10, 20, 121, 21)
        self.rdoAllLog.setChecked(True)

        # progressBar
        self.progressBar = QProgressBar(self)
        self.progressBar.setGeometry(10, 340, 251, 23)
        self.progressBar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.progressBar.setValue(0)

        # lstLog
        self.lstLog = QListWidget(self)
        self.lstLog.setGeometry(10, 32, 251, 299)
        self.lstLog.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        # lstException
        self.lstException = QListWidget(self)
        self.lstException.setGeometry(274, 250, 231, 111)
        self.lstException.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        # chkSaveLog
        self.chkSaveLog = QCheckBox("ذخیره گزارشات در فایل", self)
        self.chkSaveLog.setGeometry(690, 250, 141, 20)

        # cmbTypeException
        self.cmbTypeException = QComboBox(self)
        self.cmbTypeException.setGeometry(514, 320, 69, 22)
        self.cmbTypeException.addItems(("فایل", "پوشه", "نوع فایل"))

        # PyCrypt
        self.setWindowTitle('PyCrypt3')
        self.setWindowIcon(QIcon(resource_path('img/icon.ico')))
        self.setFixedSize(850, 375)
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)


class PyCrypt(MainWindow):
    def __init__(self):
        super().__init__()
        self.Key = ""
        self.Exceptions = ([], [], [])

        # Actions
        self.btnGenKey.clicked.connect(self.btnGenKey_click)
        self.btnEncrypt.clicked.connect(self.btnEncrypt_click)
        self.btnDecrypt.clicked.connect(self.btnDecrypt_click)
        self.btnBrowseKey.clicked.connect(self.btnBrowseKey_click)
        self.btnBrowseFile.clicked.connect(self.btnBrowseFile_click)
        self.btnBrowseLog.clicked.connect(self.btnBrowseLog_click)
        self.btnAddException.clicked.connect(self.btnAddException_click)
        self.rdoKey.toggled.connect(self.rdoKey_click)
        self.rdoPass.toggled.connect(self.rdoPass_click)
        self.rdoDir.toggled.connect(self.rdoDir_click)
        self.rdoFile.toggled.connect(self.rdoFile_click)
        self.chkSaveLog.toggled.connect(self.chkSaveLog_click)
        self.cmbTypeException.currentIndexChanged.connect(self.cmbTypeException_changed)

    def btnBrowseFile_click(self):
        if self.rdoFile.isChecked():
            files = QFileDialog.getOpenFileNames(caption="فایل ها را انتخاب کنید", directory=os.getcwd())
            f = ""
            for file in files[0]:
                f += file.replace("/", "\\") + ","
            f = f[:-1]
            self.txtPathFile.setText(f)
        else:
            folder = QFileDialog.getExistingDirectory(caption="پوشه را انتخاب کنید", directory=os.getcwd())
            self.txtPathFile.setText(folder.replace("/", "\\"))

    def btnGenKey_click(self):
        File = QFileDialog.getSaveFileName(caption="محل ذخیره کلید را انتخاب کنید", filter="Key files (*.Key)",
                                           directory="Key")
        if File[0]:
            with open(File[0], "wb") as Key:
                Key.write(Fernet.generate_key())
            QMessageBox.about(self, "پیغام", "کلید شما با موفقیت ساخته شد")
            self.txtPathKey.setText(File[0])

    def btnBrowseKey_click(self):
        File = QFileDialog.getOpenFileName(caption="کلید را انتخاب کنید", filter="Key files (*.Key)",
                                           directory=os.getcwd())
        self.txtPathKey.setText(File[0])

    def btnBrowseLog_click(self):
        File = QFileDialog.getSaveFileName(caption="محل ذخیره فایل گزارش را انتخاب کنید", filter="Text files (*.txt)",
                                           directory="logger")
        if File[0]:
            self.txtPathLog.setText(File[0].replace("/", "\\"))

    def rdoKey_click(self):
        self.lblPathKey.setText("آدرس کلید : ")
        self.lblPathKey.setGeometry(561, 90, 65, 20)
        self.txtPathKey.setEchoMode(QLineEdit.EchoMode.Normal)
        self.txtPathKey.setMaxLength(self.txtPathFile.maxLength())
        self.btnBrowseKey.show()
        self.lblPassword.hide()
        self.txtPathKey.clear()

    def rdoPass_click(self):
        self.lblPathKey.setText("پسورد : ")
        self.lblPathKey.setGeometry(541, 90, 65, 20)
        self.txtPathKey.setEchoMode(QLineEdit.EchoMode.Password)
        self.txtPathKey.setMaxLength(10)
        self.btnBrowseKey.hide()
        self.lblPassword.show()
        self.txtPathKey.clear()

    def rdoFile_click(self):
        self.lblPathFile.setText("آدرس فایل : ")
        self.txtPathFile.clear()

    def rdoDir_click(self):
        self.lblPathFile.setText("آدرس پوشه : ")
        self.txtPathFile.clear()

    def check_requirement(self):
        if self.rdoFile.isChecked():
            if self.txtPathFile.text():
                Files = self.txtPathFile.text().split(",")
                for File in Files:
                    if not os.path.isfile(File):
                        QMessageBox.about(self, "خطا", f"فایل {File} وجود ندارد")
                        return
            else:
                QMessageBox.about(self, "خطا", "آدرس فایل وارد نشده است")
                return
        else:
            if self.txtPathFile.text():
                if not os.path.isdir(self.txtPathFile.text()):
                    QMessageBox.about(self, "خطا", f"پوشه {self.txtPathFile.text()} وجود ندارد")
                    return
            else:
                QMessageBox.about(self, "خطا", "آدرس پوشه وارد نشده است")
                return

        if self.rdoKey.isChecked():
            if self.txtPathKey.text():
                if os.path.isfile(self.txtPathKey.text()):
                    try:
                        with open(self.txtPathKey.text(), 'rb') as Key:
                            self.Key = Key.read()
                        try:
                            Fernet(self.Key).encrypt(b'Test')
                        except:
                            QMessageBox.about(self, "خطا", "کلید نامعتبر است")
                            return
                    except:
                        QMessageBox.about(self, "خطا", "کلید اشتباه است")
                        return
                else:
                    QMessageBox.about(self, "خطا", f"کلید {self.txtPathKey.text()} وجود ندارد")
                    return
            else:
                QMessageBox.about(self, "خطا", "آدرس کلید وارد نشده است")
                return
        else:
            if self.txtPathKey.text():
                self.Key = self.txtPathKey.text() * 4 + "abc="
                try:
                    Fernet(self.Key).encrypt(b'Test')
                except:
                    QMessageBox.about(self, "خطا", "پسورد نامعتبر است")
                    return
            else:
                QMessageBox.about(self, "خطا", "پسورد وارد نشده است")
                return
        return True

    def crypt(self, job):
        file_log = log = ""
        if self.rdoDir.isChecked():
            Files = find_file(self.txtPathFile.text())
            NumFile = number_of_files(self.txtPathFile.text())
        else:
            Files = self.txtPathFile.text().split(",")
            NumFile = len(Files)
        k = i = 0
        self.progressBar.setValue(0)
        self.lstLog.clear()
        if self.chkSaveLog.isChecked():
            try:
                file_log = open(self.txtPathLog.text(), 'w')
                print("-" * 30 + "Start" + "-" * 30, file=file_log)
            except:
                QMessageBox.about(self, "خطا", "امکان ایجاد فایل گزارش وجود ندارد")
                return
        try:
            for file in Files:
                self.lstLog.insertItem(i, file)
                if check_exception(file, self.Exceptions):
                    try:
                        if job:
                            Encrypt_file(file, self.Key)
                            if not self.rdoUnsuccessLog.isChecked():
                                log = f"Encrypted -> {file}"
                        else:
                            Decrypt_file(file, self.Key)
                            if not self.rdoUnsuccessLog.isChecked():
                                log = f"Decrypted -> {file}"
                        self.lstLog.item(i).setBackground(QBrush(QColor(50, 255, 50)))
                    except:
                        self.lstLog.item(i).setBackground(QBrush(QColor(255, 50, 50)))
                        if not self.rdoSuccessLog.isChecked():
                            if job:
                                log = f"Cannot Encrypted -> {file}"
                            else:
                                log = f"Cannot Decrypted -> {file}"
                else:
                    self.lstLog.item(i).setBackground(QBrush(QColor(0, 200, 255)))
                    log = f"Exception -> {file}"
                if NumFile >= 100:
                    if k == int(NumFile / 100):
                        self.progressBar.setValue(self.progressBar.value() + 1)
                        k = 0
                else:
                    self.progressBar.setValue(self.progressBar.value() + int(100 / NumFile))
                k += 1
                i += 1
                if self.chkSaveLog.isChecked() and log:
                    print(log, file=file_log)
                self.update()
            self.progressBar.setValue(100)
            QMessageBox.about(self, "پیغام", "رمزگذاری تمام شد") if job \
                else QMessageBox.about(self, "پیغام", "رمزگشایی تمام شد")
            if self.chkSaveLog.isChecked():
                print("-" * 31 + "End" + "-" * 31, file=file_log)
        except:
            QMessageBox.about(self, "خطا", "دسترسی به فایل / پوشه امکان پذیر نیست")

    def btnEncrypt_click(self):
        if self.check_requirement():
            self.crypt(True)

    def btnDecrypt_click(self):
        if self.check_requirement():
            self.crypt(False)

    def chkSaveLog_click(self):
        if self.chkSaveLog.isChecked():
            self.lblPathLog.setEnabled(True)
            self.txtPathLog.setEnabled(True)
            self.btnBrowseLog.setEnabled(True)
            self.grpLevelLog.setEnabled(True)
            self.txtPathLog.setText(os.getcwd() + os.sep + "logger.txt")
        else:
            self.lblPathLog.setEnabled(False)
            self.txtPathLog.setEnabled(False)
            self.btnBrowseLog.setEnabled(False)
            self.grpLevelLog.setEnabled(False)
            self.txtPathLog.clear()

    def cmbTypeException_changed(self):
        if self.cmbTypeException.currentIndex() == 2:
            self.lblTypeFileException.show()
            self.txtTypeFile.show()
        else:
            self.lblTypeFileException.hide()
            self.txtTypeFile.hide()

    def btnAddException_click(self):
        if self.cmbTypeException.currentIndex() == 0:
            files = QFileDialog.getOpenFileNames(caption="فایل ها را انتخاب کنید", directory=os.getcwd())
            for file in files[0]:
                if file not in self.Exceptions[0]:
                    self.Exceptions[0].append(file.replace("/", "\\"))
                    self.lstException.addItem(file.replace("/", "\\"))
        elif self.cmbTypeException.currentIndex() == 1:
            folder = QFileDialog.getExistingDirectory(caption="پوشه را انتخاب کنید", directory=os.getcwd()).replace(
                "/", "\\")
            if folder:
                if folder not in self.Exceptions[1]:
                    self.Exceptions[1].append(folder)
                    self.lstException.addItem(folder)
        else:
            if not self.txtTypeFile.text():
                QMessageBox.about(self, "خطا", "نوع فایل وارد نشده است")
                return
            type_file = self.txtTypeFile.text().strip("*.").lower()
            if type_file not in self.Exceptions[2]:
                self.Exceptions[2].append(type_file)
                self.lstException.addItem(f"*.{type_file}")


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def find_file(path):
    for path, _, file in os.walk(path):
        for f in file:
            yield f"{path.replace('/', '\\')}\\{f}"


def number_of_files(path):
    i = 0
    for _, _, a in os.walk(path):
        for _ in a:
            i += 1
    return i


def Encrypt_file(file, key):
    if os.path.getsize(file) > 13981112:
        with open(file, 'rb') as thefile:
            f = thefile.read(10485760)
        f_enc = Fernet(key).encrypt(f)
        with open(file, 'r+b') as thefile:
            thefile.write(f_enc)
    else:
        with open(file, 'rb') as thefile:
            f = thefile.read()
        f_enc = Fernet(key).encrypt(f)
        with open(file, 'wb') as thefile:
            thefile.write(f_enc)


def Decrypt_file(file, key):
    if os.path.getsize(file) > 18641572:
        with open(file, 'rb') as thefile:
            f = thefile.read(13981112)
        f_enc = Fernet(key).decrypt(f)
        with open(file, 'r+b') as thefile:
            thefile.write(f_enc)
    else:
        with open(file, 'rb') as thefile:
            f = thefile.read()
        f_enc = Fernet(key).decrypt(f)
        with open(file, 'wb') as thefile:
            thefile.write(f_enc)


def check_exception(file: str, exceptions):
    if exceptions[0]:
        if file in exceptions[0]:
            return
    if exceptions[1]:
        if file.startswith(tuple(exceptions[1])):
            return
    if exceptions[2]:
        if file[file.rfind(".") + 1:].lower() in exceptions[2]:
            return
    return True


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PyCrypt()
    window.show()
    sys.exit(app.exec())
