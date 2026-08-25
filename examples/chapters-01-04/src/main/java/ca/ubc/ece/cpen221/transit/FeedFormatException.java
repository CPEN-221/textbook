package ca.ubc.ece.cpen221.transit;

import java.io.Serial;

/** Indicates that external transit-feed text does not satisfy its format. */
public final class FeedFormatException extends Exception {
    @Serial
    private static final long serialVersionUID = 1L;

    public FeedFormatException(String message) {
        super(message);
    }

    public FeedFormatException(String message, Throwable cause) {
        super(message, cause);
    }
}

