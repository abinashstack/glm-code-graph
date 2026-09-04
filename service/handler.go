package service

import (
	"fmt"

	"glmdemo/service/util"
)

// HandleLogin normalizes the username and logs the attempt.
func HandleLogin(username string) string {
	name := util.Normalize(username)
	return fmt.Sprintf("login attempt: %s", name)
}
