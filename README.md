
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic

python manage.py runserver 0.0.0.0:8000

gunicorn --bind 0.0.0.0:8000 your_project_name.wsgi:application
sudo systemctl daemon-reload
sudo systemctl restart gunicorn

sudo systemctl status gunicorn


# 가상환경 활성화 
source venv/bin/activate

# 마이그레이션 활성화 
python manage.py migrate game --fake-initial

# 서버 실행 
python manage.py runserver