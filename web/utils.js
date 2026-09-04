"use strict";

/** Format a user's display name from parts. */
function formatName(first, last) {
  return `${first} ${last}`.trim();
}

module.exports = { formatName };
