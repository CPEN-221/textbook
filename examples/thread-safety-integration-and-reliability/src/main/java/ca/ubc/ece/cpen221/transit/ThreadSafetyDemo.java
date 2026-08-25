package ca.ubc.ece.cpen221.transit;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Function;
import java.util.function.UnaryOperator;

public final class ThreadSafetyDemo {
    private ThreadSafetyDemo() { }

    public record BoardSnapshot(long version, Instant observedAt,
                                Map<String, Integer> predictions) {
        public BoardSnapshot {
            predictions = Map.copyOf(predictions);
        }
    }

    public static final class SnapshotStore {
        private final AtomicReference<BoardSnapshot> current;

        public SnapshotStore(BoardSnapshot initial) {
            current = new AtomicReference<>(initial);
        }

        public BoardSnapshot read() {
            return current.get();
        }

        public BoardSnapshot update(UnaryOperator<BoardSnapshot> operation) {
            return current.updateAndGet(operation);
        }
    }

    public static final class PredictionCache {
        private final ConcurrentHashMap<String, Integer> cache =
                new ConcurrentHashMap<>();

        public int get(String stop, Function<String, Integer> provider) {
            return cache.computeIfAbsent(stop, provider);
        }
    }

    public static void main(String[] args) throws InterruptedException {
        SnapshotStore store = new SnapshotStore(new BoardSnapshot(
                0, Instant.EPOCH, Map.of("R4", 7)));
        Runnable update = () -> {
            for (int iteration = 0; iteration < 1_000; iteration++) {
                store.update(old -> new BoardSnapshot(
                        old.version() + 1, old.observedAt(), old.predictions()));
            }
        };
        Thread first = Thread.ofVirtual().start(update);
        Thread second = Thread.ofVirtual().start(update);
        first.join();
        second.join();
        System.out.println("version=" + store.read().version());
    }
}
