from concurrent import futures
import grpc
import clicker_pb2
import clicker_pb2_grpc

class ClickerService(clicker_pb2_grpc.ClickerServiceServicer):
    def Calculate(self, request, context):
        old_val = request.current_value
        # --- Logic: เปลี่ยนจาก +1 เป็น +2 ตรงนี้ ---
        new_val = old_val * 2
        print(f"Plugin received: {old_val} -> responding: {new_val}")
        return clicker_pb2.ClickReply(new_value=new_val)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    clicker_pb2_grpc.add_ClickerServiceServicer_to_server(ClickerService(), server)
    server.add_insecure_port('[::]:50051')
    print("Plugin Server started on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()