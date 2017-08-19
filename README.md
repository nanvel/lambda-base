# Lambda base

Manage your lambda fleet.

## Installation

```bash
virtualenv .venv --no-site-packages -p python3.6
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

`python manage.py <entity> <command> <*arguments>`

```text
python manage.py lambda status
python manage.py function list
python manage.py function status <function name>
python manage.py function deploy <function name>
python manage.py function update <function name>
python manage.py function delete <function name>
python manage.py function invoke <function name> <args>
python manage.py alias list <function name>
python manage.py alias use <function name> <alias name> <function version>
python manage.py alias delete <function name> <alias name>
python manage.py alias status <function name> <alias name>
```

## Role

Lambda basic execution role (create it using IAM):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```
