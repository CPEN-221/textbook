package ca.ubc.ece.cpen221.transit;

import static java.nio.charset.StandardCharsets.UTF_8;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class PredictionFileTest {
    @TempDir
    Path temporaryDirectory;

    @Test
    void loadsUtf8FileInLineOrder() throws IOException, FeedFormatException {
        Path feed = temporaryDirectory.resolve("predictions.txt");
        Files.write(feed, List.of("UBC_EXCHANGE|0", "WESBROOK_MALL|7"), UTF_8);

        assertEquals(List.of(
                new ArrivalPrediction(new StopId("UBC_EXCHANGE"), 0),
                new ArrivalPrediction(new StopId("WESBROOK_MALL"), 7)),
                PredictionFile.load(feed));
    }

    @Test
    void reportsMalformedLine() throws IOException {
        Path feed = temporaryDirectory.resolve("predictions.txt");
        Files.writeString(feed, "UBC_EXCHANGE|soon", UTF_8);

        assertThrows(FeedFormatException.class, () -> PredictionFile.load(feed));
    }
}
