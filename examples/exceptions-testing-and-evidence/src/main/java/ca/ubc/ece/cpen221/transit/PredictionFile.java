package ca.ubc.ece.cpen221.transit;

import static java.nio.charset.StandardCharsets.UTF_8;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Loads prediction lines from UTF-8 text files. */
public final class PredictionFile {
    private PredictionFile() { }

    /**
     * Loads every prediction in a file.
     *
     * @param path the UTF-8 prediction file
     * @return an unmodifiable list in file order
     * @throws IOException if the file cannot be read
     * @throws FeedFormatException if a line is malformed
     */
    public static List<ArrivalPrediction> load(Path path)
            throws IOException, FeedFormatException {
        try (BufferedReader reader = Files.newBufferedReader(path, UTF_8)) {
            List<ArrivalPrediction> predictions = new ArrayList<>();
            String line;
            while ((line = reader.readLine()) != null) {
                predictions.add(PredictionParser.parse(line));
            }
            return List.copyOf(predictions);
        }
    }
}
