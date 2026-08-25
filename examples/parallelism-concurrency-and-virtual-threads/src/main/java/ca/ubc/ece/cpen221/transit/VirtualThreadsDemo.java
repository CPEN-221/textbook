package ca.ubc.ece.cpen221.transit;

import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.Semaphore;

public final class VirtualThreadsDemo {
    private VirtualThreadsDemo() { }

    public record StopId(String value) { }

    public record Prediction(int minutes) { }

    public interface Provider {
        Prediction fetch(StopId stop) throws InterruptedException;
    }

    public static final class LimitedProvider {
        private final Semaphore providerPermits = new Semaphore(50);
        private final Provider provider;

        public LimitedProvider(Provider provider) {
            this.provider = provider;
        }

        public Prediction fetch(StopId stop) throws InterruptedException {
            providerPermits.acquire();
            try {
                return provider.fetch(stop);
            } finally {
                providerPermits.release();
            }
        }
    }

    public static List<Integer> fetchAll(List<Callable<Integer>> requests)
            throws InterruptedException {
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<Integer>> futures = executor.invokeAll(requests);
            return futures.stream().map(VirtualThreadsDemo::get).toList();
        }
    }

    private static int get(Future<Integer> future) {
        try {
            return future.get();
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted", error);
        } catch (ExecutionException error) {
            throw new IllegalStateException("request failed", error.getCause());
        }
    }

    public static void main(String[] args) throws Exception {
        List<Integer> predictions = fetchAll(List.of(
                () -> 7,
                () -> 4,
                () -> 11));
        System.out.println("predictions=" + predictions);
    }
}
