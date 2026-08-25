package ca.ubc.ece.cpen221.transit;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public final class StreamDemo {
    private StreamDemo() { }

    public record ArrivalObservation(String route, int delayMinutes,
                                     boolean complete) { }

    public record Route(List<String> stops) {
        public Route {
            stops = List.copyOf(stops);
        }
    }

    public static Map<String, Double> meanDelayByRoute(
            List<ArrivalObservation> observations) {
        return observations.stream()
                .filter(ArrivalObservation::complete)
                .collect(Collectors.groupingBy(
                        ArrivalObservation::route,
                        LinkedHashMap::new,
                        Collectors.averagingInt(
                                ArrivalObservation::delayMinutes)));
    }

    public static List<String> distinctStops(List<Route> routes) {
        Stream<List<String>> stopLists = routes.stream().map(Route::stops);
        if (stopLists.isParallel()) {
            throw new AssertionError("unexpected parallel stream");
        }
        return routes.stream()
                .flatMap(route -> route.stops().stream())
                .distinct()
                .toList();
    }

    public static List<String> collectRoutes(
            List<ArrivalObservation> observations) {
        return observations.stream()
                .filter(ArrivalObservation::complete)
                .map(ArrivalObservation::route)
                .toList();
    }

    public static long unsafeRemovalExample(
            List<ArrivalObservation> source) {
        List<ArrivalObservation> observations = new ArrayList<>(source);
        return observations.stream()
                .filter(observation -> {
                    if (!observation.complete()) {
                        observations.remove(observation);
                    }
                    return observation.complete();
                })
                .count();
    }

    public static void main(String[] args) {
        List<ArrivalObservation> observations = List.of(
                new ArrivalObservation("R4", 3, true),
                new ArrivalObservation("99", 8, true),
                new ArrivalObservation("R4", 5, true),
                new ArrivalObservation("99", 0, false));
        System.out.println(meanDelayByRoute(observations));
    }
}
