
# API Test Evidence

## Positive Scenarios

**1. Health Check Test (GET /health)**
```text
(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i [http://127.0.0.1:5001/health](http://127.0.0.1:5001/health)
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:43:44 GMT
Content-Type: application/json
Content-Length: 44
Connection: close

{"database":"connected","status":"healthy"}

2. Get All Students (GET /students)
Plaintext

(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i [http://127.0.0.1:5001/students](http://127.0.0.1:5001/students)
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:44:12 GMT
Content-Type: application/json
Content-Length: 310
Connection: close

[{"address":"Cairo, Egypt","age":23,"email":"mawada@test.com","id":1,"name":"Mawada","phone":"01012345678"},{"address":"Giza, Egypt","age":25,"email":"mawada2@test.com","id":2,"name":"Another Student","phone":"01155556666"},{"address":null,"age":20,"email":"test1@test.com","id":3,"name":"Test","phone":null}]

3. Create Student (POST /students)
Plaintext

(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i -X POST -H "Content-Type: application/json" -d '{"name": "Ahmed", "email": "ahmed@test.com", "age": 22}' [http://127.0.0.1:5001/students](http://127.0.0.1:5001/students)
HTTP/1.1 201 CREATED
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:45:01 GMT
Content-Type: application/json
Content-Length: 86
Connection: close

{"address":null,"age":22,"email":"ahmed@test.com","id":4,"name":"Ahmed","phone":null}

## Negative Scenarios

1. Student Not Found (GET /students/<invalid_id>)
Plaintext

(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i [http://127.0.0.1:5001/students/9999](http://127.0.0.1:5001/students/9999)
HTTP/1.1 404 NOT FOUND
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:45:21 GMT
Content-Type: application/json
Content-Length: 32
Connection: close

{"message":"Student not found"}

2. Missing/Invalid Data (POST /students)
Plaintext

(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i -X POST -H "Content-Type: application/json" -d '{"age": 22}' [http://127.0.0.1:5001/students](http://127.0.0.1:5001/students)
HTTP/1.1 400 BAD REQUEST
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:45:45 GMT
Content-Type: application/json
Content-Length: 88
Connection: close

{"errors":["Name is required","Email must not be empty"],"message":"Validation failed"}

3. Invalid Request Method (POST /health)
Plaintext

(venv) moada-arafa@moada-arafa-HP-255-G8-Notebook-PC:~/StudentAPI$ curl -i -X POST [http://127.0.0.1:5001/health](http://127.0.0.1:5001/health)
HTTP/1.1 405 METHOD NOT ALLOWED
Server: Werkzeug/3.1.8 Python/3.12.3
Date: Fri, 04 Sep 2026 00:46:06 GMT
Content-Type: application/json
Content-Length: 61
Connection: close

{"error":"Method Not Allowed","path":"/health","status":405}