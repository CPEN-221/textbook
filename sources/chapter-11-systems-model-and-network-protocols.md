# Chapter 11 | Systems Model and Network Protocols

> No man is an island, entire of itself; every man is a piece of the continent, a
> part of the main.
>
> <cite>John Donne, “Meditation XVII”</cite>

The journey planner has so far received transit data through Java method calls and
local files. A deployed client may instead request predictions from another process.
The server can be on the same computer, in a nearby data centre, or temporarily
unreachable.

A method call has one runtime and one memory model. A network exchange crosses
process boundaries. The sender must encode values as bytes, the receiver must know
where one message ends, and both sides must agree on the meaning of every response.
Delay and partial failure become normal outcomes rather than unusual defects.

We will build a small local protocol for one prediction request. Its simplicity lets
us inspect every byte-level decision. We then relate those decisions to Hypertext
Transfer Protocol (HTTP), Java's HTTP client, and production concerns such as
encryption, timeouts, and retries.

By the end of this chapter, you should be able to:

- distinguish a process, host, address, port, socket, and protocol;
- specify message syntax, framing, character encoding, and response meaning;
- implement one request-response exchange over a Transmission Control Protocol
  (TCP) socket;
- handle end-of-stream, malformed data, timeout, and connection failure separately;
- explain what HTTP supplies above a byte stream;
- use an HTTP status and body as separate parts of a response contract; and
- decide whether an operation may be retried without changing its intended effect.

## 1. Participants and Connection Endpoints

A **process** is a running program with its own address space and operating-system
resources. A client process requests a service; a server process accepts requests and
produces responses. These are roles in an interaction. One program can act as a
client in one exchange and a server in another.

A network interface has an Internet Protocol (IP) address. A **port** is a numbered
endpoint used to direct traffic to a process or service on a host. The pair of address
and port identifies one endpoint for TCP communication.

A host name such as `predictions.example` is not an address. A resolver, commonly
using the Domain Name System (DNS), maps the name to one or more addresses. Resolution
can fail, change over time, or return several candidates. A connected socket records
the actual local and remote endpoints selected for that connection; it does not make
the host name a permanent identity for the server. The application still authenticates
the service according to its security policy.

A Java `Socket` represents one endpoint of an established TCP connection. A
`ServerSocket` listens for connection requests on a local port; `accept` returns a
new connected `Socket` for one accepted connection. The listening socket continues
to represent the service endpoint and can accept later connections.

TCP gives the application a reliable, ordered stream of bytes between connected
endpoints. It does not preserve application message boundaries. If a sender performs
two writes, the receiver may obtain the bytes through one read or many reads. The
application protocol must define its own framing.

A **protocol** specifies the rules both participants follow. For our prediction
service, it must answer at least four questions:

- which request and response messages are valid;
- how text becomes bytes;
- how a receiver finds the end of a message; and
- what each valid message means.

> **Design principle:** Treat every process boundary as an explicit data and failure
> boundary. Specify bytes, framing, meaning, and time limits before relying on the
> exchange.

## 2. A Small Prediction Protocol

The request grammar is:

```text
request  = "GET" SP stop-id LF
stop-id  = 1*16(ALPHA / DIGIT / "_")
```

A successful response is:

```text
"OK" SP minutes LF
```

An error response is:

```text
"ERR" SP error-code LF
```

All text is encoded using Unicode Transformation Format, 8-bit form (UTF-8). A line
feed byte terminates each message. `minutes` is a base-ten non-negative integer. The
first version recognises `UNKNOWN_STOP` as an error code.

This specification is intentionally small, but it removes several ambiguities. A
reader knows that `GET UBC` without a line feed is incomplete, `OK -2` is invalid,
and platform-default encodings are not part of the protocol. A server may reject a
stop identifier longer than sixteen characters before consulting domain data.

The grammar also limits memory use. A production parser should cap the number of
bytes it accepts before a line feed. `BufferedReader.readLine` alone can allocate for
an unexpectedly long line. The compact demonstration exchanges trusted local input;
a service that accepts untrusted input needs the stated limit in its parser.

Versioning belongs in the protocol when incompatible changes become possible. We
could begin each request with `PREDICT/1`, or use a versioned media type in HTTP. A
new server can then distinguish an old client from a malformed current request.

## 3. The Client Exchange

The client connects to the server's address and port, configures a read timeout, and
creates UTF-8 text adapters over the socket byte streams:

```java
try (Socket socket = new Socket(InetAddress.getLoopbackAddress(), port)) {
    socket.setSoTimeout(2_000);
    BufferedReader input = new BufferedReader(new InputStreamReader(
            socket.getInputStream(), StandardCharsets.UTF_8));
    BufferedWriter output = new BufferedWriter(new OutputStreamWriter(
            socket.getOutputStream(), StandardCharsets.UTF_8));
    output.write("GET " + stop + "\n");
    output.flush();
    String response = input.readLine();
    // validate and interpret response
}
```

`flush` matters because the writer may retain characters in a buffer. The server is
waiting for a complete request, while the client is about to wait for a response. If
the client does not make the buffered request available to the socket, both sides can
wait without progress.

The try-with-resources statement closes the socket and its streams on both normal and
exceptional exits. Closing the socket releases the underlying operating-system
resource and signals end-of-stream to the peer as appropriate.

`setSoTimeout(2_000)` configures a two-second timeout for blocking reads on this
socket. It is an inactivity bound for a read operation, not a deadline for all work
from initial name lookup through response parsing. Production clients often need
separate connection and request deadlines.

The client validates the complete response before converting it:

```java
String response = input.readLine();
if (response == null || !response.matches("OK [0-9]+")) {
    throw new IOException("invalid response: " + response);
}
return Integer.parseInt(response.substring(3));
```

`null` means the peer ended the stream before sending a line. That outcome differs
from a valid error response. The current method accepts only successful responses;
a fuller API would parse `ERR UNKNOWN_STOP` into a domain failure distinct from a
malformed message.

The decimal grammar does not impose an upper bound small enough for `int`.
`Integer.parseInt` can therefore throw `NumberFormatException` for a syntactically
decimal but out-of-range value. A precise implementation catches that exception and
reports an invalid response, or changes the grammar to cap the numeric range.

## 4. A Deterministic Local Exchange

The companion program binds a `ServerSocket` to the loopback address and requests
port zero. Port zero asks the operating system to choose an available local port. The
program reads that assigned port and starts a server task:

```java
try (ServerSocket server = new ServerSocket(
        0, 1, InetAddress.getLoopbackAddress())) {
    Thread serverThread = new Thread(() -> serveOnce(server));
    serverThread.start();
    int minutes = requestPrediction(server.getLocalPort(), "UBC");
    serverThread.join();
    System.out.println("prediction=" + minutes);
}
```

The server accepts one connection, reads one line, and returns either `OK 7` or
`ERR UNKNOWN_STOP`. The client and server roles in this demonstration run as threads
inside one Java process, but they communicate through actual loopback TCP sockets.
The test does not depend on external transit data or Internet access.

The validated Java 25 run printed:

```text
prediction=7
```

The observation confirms one execution of the implementation. The protocol
specification, tests for all grammar cases, and analysis of failure paths remain
necessary. A successful loopback exchange does not establish that a remote firewall,
name service, or server deployment is configured correctly.

## 5. Partial Failure

A local method call either returns, throws, or does not terminate. A network call has
the same broad outcomes, but more independent causes lie between caller and callee.
The client can fail before the server sees a request, the server can act before its
response is lost, or the response can arrive after the client gives up.

Important cases include:

- name resolution cannot map a host name to an address;
- connection establishment is refused or times out;
- the peer accepts and then closes the connection;
- a read times out after a partial response;
- bytes arrive but violate the protocol grammar;
- a syntactically valid response contains a domain error; and
- the client cannot determine whether the server completed an operation.

The last case prevents a general “retry on failure” rule. Suppose a request
purchases
a fare. The server commits the purchase, but the connection fails before the client
receives the confirmation. Repeating the request may purchase twice.

An operation is **idempotent** when multiple identical requests have the same intended
effect as one such request. Reading a prediction is normally idempotent because it
does not change server state, though responses may differ as time advances. Setting a
preference to a specified value can be idempotent. Incrementing a counter or creating
a new purchase is generally not.

Retries also need bounds, delay policy, and a total deadline. Immediate retries from
many clients can increase load on an already failing service. Randomised backoff,
capacity limits, and monitoring belong to the system design, not a catch block added
after the protocol is written.

## 6. HTTP Semantics

HTTP defines a request-response application protocol with methods, target resources,
header fields, status codes, and representations. It is stateless in the sense that
each request can be understood on its own; applications can still build sessions by
carrying state in cookies, tokens, or server storage.

An HTTP version of the prediction request might use:

```text
GET /v1/stops/UBC/prediction HTTP/1.1
Host: predictions.example
Accept: application/json
```

The response contains a status code and a representation. A `200` response might
carry a JavaScript Object Notation (JSON) object with the prediction. A `404` might
mean the stop resource is unknown. A `503` reports temporary service unavailability.
The API specification must define these meanings; the status number alone does not
define the application's domain model.

JSON is a text interchange format. Networked JSON exchanged outside a closed
ecosystem must use UTF-8 under RFC 8259. A parser should validate the body against
the application's expected schema and range constraints. Successful JSON parsing
only establishes syntactic validity, not that a stop exists or minutes are
non-negative.

HTTP semantics classify `GET`, `HEAD`, `OPTIONS`, and `TRACE` as safe methods and
define several methods as idempotent. A client may automatically retry an idempotent
request after some communication failures, but it still needs application knowledge
and limits. An idempotent request can be expensive, rate-limited, or inappropriate to
repeat after its deadline.

## 7. Java's HTTP Client at the HTTP Boundary

`java.net.http.HttpClient` is immutable after construction and can send multiple
requests. Reuse allows the implementation to reuse connections when possible. A
client can perform synchronous requests with `send` or asynchronous requests with
`sendAsync`.

A synchronous request has this general structure:

```java
HttpRequest request = HttpRequest.newBuilder(endpoint)
        .timeout(Duration.ofSeconds(2))
        .header("Accept", "application/json")
        .GET()
        .build();
HttpResponse<String> response = client.send(
        request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
```

After `send`, the adapter must inspect `response.statusCode()` before interpreting
`response.body()` as a success representation. Treating every body as the same JSON
shape confuses a server error document with a prediction.

`HttpClient` provides protocol machinery; it does not supply the domain contract.
An adapter can convert the HTTP status and validated body into `Prediction` or a
specific domain exception. The rest of the planner then depends on the domain API
instead of HTTP details. This is the composition boundary from Chapter 8.

For a production endpoint, use Hypertext Transfer Protocol Secure (HTTPS), which
runs HTTP with Transport Layer Security (TLS). TLS authenticates the server according
to configured trust and protects data in transit. Certificate and host-name
verification should not be disabled to make a failing development connection pass.

## 8. Common Misconception: One `read` Receives One `write`

TCP transports an ordered byte stream. It does not expose the sender's write calls as
message records. A receiver that allocates a buffer and calls `read` once may obtain
part of a message, several application messages, or end-of-stream.

Correct code loops according to a framing rule. A fixed-length protocol reads until
the declared number of bytes arrive. A delimiter protocol scans until the delimiter
within a size limit. A length-prefixed protocol first reads and validates the length,
then reads exactly that many bytes.

Our buffered text example uses `readLine`, which loops until a line terminator or
end-of-stream. The line feed is part of the protocol. Removing it from the sender
changes the interaction even if the visible request characters are otherwise
correct.

## 9. Practice by Specifying Failures

For each exercise, write the protocol rule before the Java control flow.

1. Extend the local protocol with `ERR UNKNOWN_STOP` and `ERR BUSY`. Decide which
   response becomes a domain error and which may be retried.
2. Set a maximum response line length of 128 bytes. Explain how the parser rejects a
   longer unterminated message without retaining an unbounded buffer.
3. The server receives a valid request and closes before responding. State what the
   client knows about whether the request was processed.
4. An HTTP endpoint returns status `503` with a valid JSON error body. Explain why
   successful JSON parsing does not make the request successful.
5. A generated client retries every `POST` after a timeout. Identify the additional
   API mechanism, such as an idempotency key, needed to prevent duplicate effects.
6. Draw the listening `ServerSocket` and two connected `Socket` pairs for two
   simultaneous clients. Label the local and remote endpoints of each connection.

Then design one deterministic integration test for a timeout and one for a malformed
response. The test server should run locally, choose an available port, and control
the exact bytes it sends. State how the test ensures its server task terminates even
when the client fails.

## 10. Summary

- A network interaction connects process endpoints identified by addresses and
  ports.
- TCP supplies a reliable ordered byte stream, not application message boundaries.
- A protocol must define syntax, encoding, framing, meaning, and applicable limits.
- Network failures can leave a client uncertain about whether the server acted.
- Retry policy depends on operation semantics, especially idempotence, as well as
  deadlines and load.
- HTTP supplies standard request-response semantics; an application still defines
  resource meanings and validates bodies.
- Java's socket and HTTP APIs manage communication mechanisms. An adapter should
  translate their results into the domain contract used by the rest of the program.

## References

- John Donne. [“Meditation XVII,” *Devotions upon Emergent Occasions*](https://www.gutenberg.org/files/23772/23772-h/23772-h.htm).
- Oracle. [`Socket` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/Socket.html).
- Oracle. [`ServerSocket` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/ServerSocket.html).
- Oracle. [`HttpClient` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/java/net/http/HttpClient.html).
- R. Fielding, M. Nottingham, and J. Reschke. [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html), 2022.
- T. Bray. [RFC 8259: The JavaScript Object Notation (JSON) Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html), 2017.
- F. Yergeau. [RFC 3629: UTF-8, a Transformation Format of ISO 10646](https://www.rfc-editor.org/rfc/rfc3629.html), 2003.
