package middleware

import (
	"fmt"
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

// Logger returns a gin.HandlerFunc for logging requests
func Logger() gin.HandlerFunc {
	return gin.LoggerWithFormatter(func(param gin.LogFormatterParams) string {
		return fmt.Sprintf("%s - [%s] \"%s %s %s %d %s \"%s\" %s\"\n",
			param.ClientIP,
			param.TimeStamp.Format(time.RFC1123),
			param.Method,
			param.Path,
			param.Request.Proto,
			param.StatusCode,
			param.Latency,
			param.Request.UserAgent(),
			param.ErrorMessage,
		)
	})
}

// ErrorHandler returns a gin.HandlerFunc for handling errors
func ErrorHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()

		// Handle any errors that occurred during request processing
		if len(c.Errors) > 0 {
			err := c.Errors.Last()
			log.Printf("Request error: %v", err)

			// Return appropriate error response
			switch err.Type {
			case gin.ErrorTypeBind:
				c.JSON(400, gin.H{"error": "Invalid request format"})
			case gin.ErrorTypePublic:
				c.JSON(500, gin.H{"error": err.Error()})
			default:
				c.JSON(500, gin.H{"error": "Internal server error"})
			}
		}
	}
}

// Recovery returns a gin.HandlerFunc for recovering from panics
func Recovery() gin.HandlerFunc {
	return gin.CustomRecovery(func(c *gin.Context, recovered interface{}) {
		log.Printf("Panic recovered: %v", recovered)
		c.JSON(500, gin.H{"error": "Internal server error"})
	})
}
