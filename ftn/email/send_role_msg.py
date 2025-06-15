import sys
import os

current_file_path = os.path.abspath(__file__)
parent_dir = os.path.dirname(current_file_path)
sys.path.append(parent_dir)

from email_sender import EmailSender
es = EmailSender('./config/sender.config')

def send_role_msg(
    es:EmailSender,
    player_email:str,
    mail_subject:str,
    image_file:str,
    bold_text:str,
    plain_text:str
):
    es.clear_msg()
    es.add_img(image_file)
    es.add_heading(bold_text, 1)
    es.add_heading(plain_text, 3)
    es.send(mail_subject, player_email)



if __name__ == "__main__":
    
    send_role_msg(es,
        'cv5006@naver.com',
        'role msg test #1',
        './media/morgana.png',
        'You are Morgana',
        'blah blah and good luck'
    )

    send_role_msg(es,
        'jhy6219@naver.com',
        'role msg test #2',
        './media/percival.png',
        'You are Percival',
        'blah blah and good luck'
    )