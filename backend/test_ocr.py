# import asyncio
# from main_ocr import process_two_meters

# result = asyncio.run(process_two_meters("test_images/2.jpg", "test_images/4.jpg"))

# print(result)


from http.server import HTTPServer, SimpleHTTPRequestHandler

server = HTTPServer(("127.0.0.1", 9080), SimpleHTTPRequestHandler)
server.serve_forever()