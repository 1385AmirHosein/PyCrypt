import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from secrets import token_bytes, token_urlsafe
from shutil import copystat

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


class Files:
    @dataclass
    class _Exclusion:
        files: dict[Path, None] = field(default_factory = dict)
        folders: dict[Path, None] = field(default_factory = dict)
        extensions: dict[str, None] = field(default_factory = dict)

    def __init__(self) -> None:
        self._files: dict[Path, tuple[bool, int]] = {}
        self._exclusion: Files._Exclusion = self._Exclusion()
        self.size: int = 0
        self._total_files: int = 0
        self.failed_to_add: list[str] = []

    def __call__(self, path: str) -> Iterator[str] | list[str]:
        file: Path = Path(path).resolve()
        if file.is_file():
            return [str(file)] if self._add_file(file) else []
        elif file.is_dir():
            return self._find_files(file)
        else:
            raise FileNotFoundError(file)

    def __iter__(self) -> Iterator[tuple[Path, int, bool]]:
        for file, (included, size) in self._files.items():
            yield file, size, included

    def __contains__(self, file: str) -> bool:
        return Path(file).resolve() in self._files

    def __len__(self) -> int:
        return self._total_files

    def __bool__(self) -> bool:
        return len(self._files) != 0

    def adjust_size(self, file: Path, delta_size: int) -> None:
        self._files[file] = (self._files[file][0], self._files[file][1] + delta_size)
        self.size += delta_size

    def add_exclusion(self, items: list[str], *, folder: bool = False, suffix: bool = False) -> None:
        if folder and suffix:
            raise ValueError('An exclusion target cannot be both a folder and a suffix!')
        for item in items:
            if not item or not item.strip():
                continue
            if folder:
                self._exclusion.folders[Path(item).resolve()] = None
            elif suffix:
                if not (ext := item.strip().strip('*.').lower()):
                    continue
                self._exclusion.extensions[f".{ext}"] = None
            else:
                self._exclusion.files[Path(item).resolve()] = None
        for file, (included, size) in self._files.items():
            if included and self._is_excluded(file):
                self._files[file] = (False, size)
                self._total_files -= 1
                self.size -= size

    def get_exclusions(self) -> Iterator[str]:
        for file in self._exclusion.files:
            yield str(file)
        for folder in self._exclusion.folders:
            yield str(folder)
        yield from self._exclusion.extensions

    def remove_exclusion(self, items: list[str]) -> None:
        for item in items:
            if not item or not item.strip():
                continue
            self._exclusion.folders.pop(Path(item).resolve(), None)
            self._exclusion.extensions.pop(f".{item.strip().strip('*.').lower()}", None)
            self._exclusion.files.pop(Path(item).resolve(), None)
        for file, (included, size) in self._files.items():
            if not included and not self._is_excluded(file):
                self._files[file] = (True, size)
                self._total_files += 1
                self.size += size

    def clear_exclusion(self) -> None:
        self._exclusion.files.clear()
        self._exclusion.folders.clear()
        self._exclusion.extensions.clear()
        for file, (included, size) in self._files.items():
            if not included:
                self._files[file] = (True, size)
                self._total_files += 1
                self.size += size

    def remove_file(self, path: str) -> None:
        if (file := Path(path).resolve()) in self._files:
            if self._files[file][0]:
                self.size -= self._files[file][1]
                self._total_files -= 1
            del self._files[file]

    def clear(self) -> None:
        self._files.clear()
        self._total_files = 0
        self.size = 0

    def _find_files(self, folder: Path) -> Iterator[str]:
        for file in folder.rglob("*"):
            if not file.is_symlink() and file.is_file() and self._add_file(file):
                yield str(file)

    def _is_excluded(self, file: Path) -> bool:
        return (file in self._exclusion.files or file.suffix.lower() in self._exclusion.extensions
                or any(file.is_relative_to(folder) for folder in self._exclusion.folders))

    def _add_file(self, file: Path) -> bool:
        if file not in self._files:
            try:
                size: int = file.stat().st_size
            except Exception as e:
                self.failed_to_add.append(str(file))
                if sys.stdout:
                    print(type(e), ':', e)
                return False
            if self._is_excluded(file):
                self._files[file] = (False, size)
            else:
                self._files[file] = (True, size)
                self._total_files += 1
                self.size += size
            return True
        else:
            return False


class CipherEngine:
    _KEY_SIZE: int = 32
    _NONCE_SIZE: int = 12
    _CHUNK_SIZE: int = 1024 * 1024
    _SALT: bytes = b'*PyCrypt*'
    _MAGIC: bytes = b'AESg-enc'
    PASSWORD_SIZE: int = 12
    HEADER_SIZE: int = len(_MAGIC) + _NONCE_SIZE + 16

    class FileTooBig(Exception):
        pass

    class KeyNotFound(Exception):
        pass

    class NotEncrypted(Exception):
        pass

    class DecryptionFailed(Exception):
        pass

    def __init__(self) -> None:
        self._key: bytes = b''
        self.is_key_set: bool = False

    def generate_key(self) -> bytes:
        return token_bytes(self._KEY_SIZE)

    def set_key(self, key: bytes) -> None:
        if len(key) != self._KEY_SIZE:
            raise ValueError("Key size is incorrect!")
        self._key = key
        self.is_key_set = True

    def generate_password(self) -> str:
        password: str = token_urlsafe(self.PASSWORD_SIZE)[:self.PASSWORD_SIZE]
        self.set_password(password)
        return password

    def set_password(self, password: str) -> None:
        kdf = Argon2id(salt = self._SALT, length = self._KEY_SIZE, iterations = 3, lanes = 4, memory_cost = 65536)
        self._key = kdf.derive(password.encode('utf-8'))
        self.is_key_set = True

    def clear_key(self) -> None:
        self._key = b''
        self.is_key_set = False

    def encrypt(self, file: Path, size: int, on_progress: Callable[[int], None], temp: bool = True) -> None:
        if not self._key:
            raise self.KeyNotFound("Key is missing!")
        if size > ((1 << 36) - 32):
            raise self.FileTooBig("File Larger than 64GB!")
        nonce: bytes = token_bytes(self._NONCE_SIZE)
        encryptor = Cipher(algorithms.AES(self._key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(self._MAGIC + nonce)
        file_out: Path = file
        if temp:
            file_out = file.with_name(file.name + ".pycrypt_tmp")
            file_out.write_bytes(b'')
        try:
            with open(file, "rb") as input_file, open(file_out, "r+b") as output_file:
                first_chunk: bytes = input_file.read(self._CHUNK_SIZE)
                output_file.write(self._MAGIC)
                output_file.write(nonce)
                output_file.write(b'\x00' * 16)
                file_chunk: bytes = encryptor.update(first_chunk)
                on_progress(len(file_chunk))
                while chunk := input_file.read(self._CHUNK_SIZE):
                    output_file.write(file_chunk)
                    file_chunk = encryptor.update(chunk)
                    on_progress(len(chunk))
                    if len(chunk) < self._CHUNK_SIZE:
                        break
                output_file.write(file_chunk)
                output_file.write(encryptor.finalize())
                output_file.seek(len(self._MAGIC) + self._NONCE_SIZE)
                output_file.write(encryptor.tag)
            if temp:
                copystat(file, file_out)
                file_out.replace(file)
        except Exception:
            if temp:
                file_out.unlink()
            raise

    def decrypt(self, file: Path, size: int, on_progress: Callable[[int], None], temp: bool = True) -> None:
        if not self._key:
            raise self.KeyNotFound("Key is missing!")
        file_out: Path = file
        if size < self.HEADER_SIZE:
            raise self.NotEncrypted("File is too small!")
        if temp:
            file_out = file.with_name(file.name + ".pycrypt_tmp")
            file_out.write_bytes(b'')
        try:
            with open(file, "rb") as input_file, open(file_out, "r+b") as output_file:
                if (magic := input_file.read(len(self._MAGIC))) != self._MAGIC:
                    raise self.NotEncrypted("file is not encrypted!")
                nonce: bytes = input_file.read(self._NONCE_SIZE)
                tag: bytes = input_file.read(16)
                on_progress(self.HEADER_SIZE)
                decryptor = Cipher(algorithms.AES(self._key), modes.GCM(nonce, tag)).decryptor()
                decryptor.authenticate_additional_data(magic + nonce)
                while chunk := input_file.read(self._CHUNK_SIZE):
                    output_file.write(decryptor.update(chunk))
                    on_progress(len(chunk))
                output_file.write(decryptor.finalize())
                output_file.truncate()
            if temp:
                copystat(file, file_out)
                file_out.replace(file)
        except InvalidTag as e:
            if temp:
                file_out.unlink()
            else:
                file_out.replace(file_out.with_stem(f'{file_out.stem}-CORRUPTED'))
            raise self.DecryptionFailed("Wrong Passkey or Wrong File") from e
        except Exception:
            if temp:
                file_out.unlink()
            raise
