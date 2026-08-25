package ca.ubc.ece.cpen221.transit;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

public final class ProtocolDemo {
    private ProtocolDemo() { }

    public static int requestPrediction(int port, String stop) throws IOException {
        try (Socket socket = new Socket(InetAddress.getLoopbackAddress(), port)) {
            socket.setSoTimeout(2_000);
            BufferedReader input = new BufferedReader(new InputStreamReader(
                    socket.getInputStream(), StandardCharsets.UTF_8));
            BufferedWriter output = new BufferedWriter(new OutputStreamWriter(
                    socket.getOutputStream(), StandardCharsets.UTF_8));
            output.write("GET " + stop + "\n");
            output.flush();
            String response = input.readLine();
            if (response == null || !response.matches("OK [0-9]+")) {
                throw new IOException("invalid response: " + response);
            }
            return Integer.parseInt(response.substring(3));
        }
    }

    public static HttpResponse<String> requestHttp(
            HttpClient client, URI endpoint) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(endpoint)
                .timeout(Duration.ofSeconds(2))
                .header("Accept", "application/json")
                .GET()
                .build();
        return client.send(
                request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    public static void main(String[] args) throws Exception {
        try (ServerSocket server = new ServerSocket(
                0, 1, InetAddress.getLoopbackAddress())) {
            Thread serverThread = new Thread(() -> serveOnce(server));
            serverThread.start();
            int minutes = requestPrediction(server.getLocalPort(), "UBC");
            serverThread.join();
            System.out.println("prediction=" + minutes);
        }
    }

    private static void serveOnce(ServerSocket server) {
        try (Socket socket = server.accept();
             BufferedReader input = new BufferedReader(new InputStreamReader(
                     socket.getInputStream(), StandardCharsets.UTF_8));
             BufferedWriter output = new BufferedWriter(new OutputStreamWriter(
                     socket.getOutputStream(), StandardCharsets.UTF_8))) {
            String request = input.readLine();
            output.write("GET UBC".equals(request) ? "OK 7\n" : "ERR UNKNOWN_STOP\n");
            output.flush();
        } catch (IOException error) {
            throw new IllegalStateException(error);
        }
    }
}
