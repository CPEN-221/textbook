package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.Test;

class ArrivalBoardTest {
    private static final Departure R4 =
            new Departure(new StopId("A"), "R4", 8);
    private static final Departure NINETY_NINE =
            new Departure(new StopId("B"), "99", 2);

    @Test
    void constructorDetachesFromMutableInputList() {
        List<Departure> source = new ArrayList<>(List.of(R4, NINETY_NINE));
        ArrivalBoard board = new ArrivalBoard(source);

        source.clear();

        assertEquals(List.of(R4, NINETY_NINE), board.upcoming());
    }

    @Test
    void clientCannotReorderBoard() {
        ArrivalBoard board = new ArrivalBoard(List.of(R4, NINETY_NINE));

        assertThrows(UnsupportedOperationException.class,
                () -> board.upcoming().sort(
                        Comparator.comparingInt(Departure::minutesUntilArrival)));
        assertEquals(List.of("R4", "99"),
                board.upcoming().stream().map(Departure::routeName).toList());
    }
}

