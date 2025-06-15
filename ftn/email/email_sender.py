import csv
import smtplib
import ssl
import uuid

import mimetypes
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from dominate import document
from dominate.tags import *


class EmailSender:
    def __init__(self, sender_config:str, receivers_file:str|None=None):
        self.msg = MIMEMultipart('related')
        
        try:
            with open(sender_config, 'r') as sc:
                self.smtp_server = sc.readline().strip()
                self.smtp_port = sc.readline().strip()
                self.sender_addr = sc.readline().strip()
                self.sender_pw = sc.readline().strip()
        except Exception as e:
            print(f'Failed to load sender.config: {e}')
            exit()
        
        print(f'SMTP Server: {self.smtp_server}:{self.smtp_port}')
        print(f'Sender: {self.sender_addr}')

        self.msg["From"] = self.sender_addr
        
        self.doc = document(title='html_doc')
        
        self.receivers = dict()
        if receivers_file is not None:
            self.load_email_list(receivers_file)


    def add_receiver(self, nickname:str, email_addr:str):
        self.receivers[nickname] = email_addr


    def load_email_list(self, csv_path:str):
        try:
            with open(csv_path, mode='r', newline='', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)

                for row in csv_reader:
                    nick = row[0].strip()
                    addr = row[1].strip()
                    self.add_receiver(nick, addr)

        except FileNotFoundError:
            print(f"Error: File not found '{csv_path}'")
        except IndexError:
            print(f"Error: Column index out of range for file '{csv_path}'. Check key_column_index and value_column_index.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    

    def add_img(self, img_path:str):
        img_cid = str(uuid.uuid4())

        # Edit Doc
        with self.doc:
            div(img(src=f'cid:{img_cid}'))

        # Attach Img
        try:
            with open(img_path, 'rb') as fp:
                img_data = fp.read()

            _, subtype = mimetypes.guess_type(img_path)[0].split('/')
            msg_image = MIMEImage(img_data, _subtype=subtype)
            msg_image.add_header('Content-ID', f'<{img_cid}>')
            self.msg.attach(msg_image)

        except FileNotFoundError:
            print(f"Error: Image file '{img_path}' not found.")
        except TypeError: # mimetypes.guess_type might return None if it can't guess
            print(f"Error: Could not determine MIME type for image '{img_path}'. Is it a valid image file?")
        except Exception as e:
            print(f"Error preparing image attachment: {e}")


    def add_heading(self, txt:str, level:int=4):
        with self.doc:
            if level == 1:
                h1(txt)
            elif level == 2:
                h2(txt)
            elif level == 3:
                h3(txt)
            elif level == 4:
                h4(txt)


    def add_text(self, txt:str):
        with self.doc:
            p(txt)


    def clear_msg(self):
        self.msg = MIMEMultipart('related')
        self.msg["From"] = self.sender_addr
        self.doc = document(title='html_doc')


    def send(self, subject:str, receiver_addr:str):
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as srv:
                sender_addr = self.msg["From"]
                self.msg["To"] = receiver_addr
                self.msg["Subject"] = subject
                self.msg.attach(MIMEText(self.doc.render(), 'html'))

                context = ssl.create_default_context()
                srv.starttls(context=context)
                srv.login(sender_addr, password=self.sender_pw)
                srv.send_message(self.msg)
                print("Email sent successfully!")
                
        except Exception as e:
            print(f"Error sending email: {e}")
            raise e


if __name__ == "__main__":
    es = EmailSender(
        sender_config='config/sender.config',
        receivers_file='./config/receivers.csv'
    )

    es.add_receiver('player3', 'jhy6219@naver.com')

    import os
    import time
    import random
    img_list = os.listdir('./media')
    for name, addr in es.receivers.items():
        print(f'sending to {name}: {addr}')
        es.add_img(f'./media/{random.choice(img_list)}')
        for i in range(1, 5):
            es.add_heading(f'h{i} text', i)
            es.add_text(f'text {i}')
        es.send(f"test for {name}", addr)
        es.clear_msg()
        time.sleep(1)
