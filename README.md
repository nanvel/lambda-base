# Lambda base

Manage your lambda fleet.

## Installation

```bash
virtualenv .venv --no-site-packages -p python3.6
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

`lmanage <entity> <command> *<arguments>`

lmanage.py lambda status

lmanage.py function list

lmanage.py function status <lambda function>

lmanage.py function deploy <lambda function>

lmanage.py function update <lambda function>

lmanage.py function delete <lambda function>

lmanage.py function invoke <function name> <args>

lmanage.py alias create <alias>

lmanage.py alias delete <alias>

lmanage.py alias status <alias>

lmanage.py alias use <alias> <version>

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