"use strict";

const { formatName } = require('./utils');

function renderProfile(user) {
  return `<h1>${formatName(user.first, user.last)}</h1>`;
}

module.exports = { renderProfile };
