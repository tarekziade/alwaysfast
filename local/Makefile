.PHONY: password

bin/python:
	python3 -m venv .
	bin/pip install bcrypt

password: bin/python
	bin/python create_password.py
