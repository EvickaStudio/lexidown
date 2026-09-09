// One JSON request per line; one JSON result per line. Requires npm ci.
const readline = require('node:readline')
const TurndownService = require('turndown')
const domino = require('@mixmark-io/domino')

function convert (request) {
  const service = new TurndownService(request.options)
  if (request.keep) service.keep(request.keep)
  if (request.remove) service.remove(request.remove)
  if (request.strikethrough) {
    service.use(function (instance) {
      instance.addRule('strikethrough', {
        filter: ['del', 's', 'strike'],
        replacement: content => '~~' + content + '~~'
      })
    })
  }
  if (request.escape !== undefined) return service.escape(request.escape)
  function input (html) {
    if (!request.mode || request.mode === 'string') return html
    const document = domino.createDocument('<div id="fixture-root">' + html + '</div>')
    const element = document.getElementById('fixture-root')
    if (request.mode === 'document') return document
    if (request.mode === 'fragment') {
      const fragment = document.createDocumentFragment()
      while (element.firstChild) fragment.appendChild(element.firstChild)
      return fragment
    }
    return element
  }
  if (request.sequence) return request.sequence.map(html => service.turndown(input(html)))
  return service.turndown(input(request.html))
}

readline.createInterface({ input: process.stdin, crlfDelay: Infinity }).on('line', line => {
  try {
    console.log(JSON.stringify({ result: convert(JSON.parse(line)) }))
  } catch (error) {
    console.log(JSON.stringify({ error: error.name, message: error.message }))
  }
})
