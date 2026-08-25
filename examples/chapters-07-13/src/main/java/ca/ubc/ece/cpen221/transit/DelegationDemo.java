package ca.ubc.ece.cpen221.transit;

import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class DelegationDemo {
    private DelegationDemo() { }

    public record RouteRequest(String origin, String destination,
                               boolean stepFreeRequired) { }

    public record Route(List<String> stops, boolean stepFree) {
        public Route {
            stops = List.copyOf(stops);
        }
    }

    public interface Router {
        Route route(RouteRequest request);
    }

    public static final class DirectRouter implements Router {
        @Override
        public Route route(RouteRequest request) {
            return new Route(List.of(request.origin(), request.destination()), true);
        }
    }

    public static final class AuditedRouter implements Router {
        private final Router delegate;
        private int completedRequests;

        public AuditedRouter(Router delegate) {
            this.delegate = Objects.requireNonNull(delegate);
        }

        @Override
        public Route route(RouteRequest request) {
            Route result = delegate.route(request);
            completedRequests++;
            return result;
        }

        public int completedRequests() {
            return completedRequests;
        }
    }

    public static final class CachingRouter implements Router {
        private final Router delegate;
        private final Map<RouteRequest, Route> cache = new HashMap<>();

        public CachingRouter(Router delegate) {
            this.delegate = Objects.requireNonNull(delegate);
        }

        @Override
        public Route route(RouteRequest request) {
            return cache.computeIfAbsent(request, delegate::route);
        }
    }

    public static final class RecordingRouter implements Router {
        private RouteRequest received;

        @Override
        public Route route(RouteRequest request) {
            received = request;
            return new Route(List.of("UBC", "WATERFRONT"), true);
        }

        public RouteRequest received() {
            return received;
        }
    }

    public static void main(String[] args) {
        AuditedRouter router = new AuditedRouter(new DirectRouter());
        Route route = router.route(new RouteRequest("UBC", "WATERFRONT", true));
        System.out.println(route.stops() + ", audited=" + router.completedRequests());
    }
}
