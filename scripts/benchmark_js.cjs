// One JSON request per line; HTML reads and output hashing are outside timing.
const { createHash } = require('node:crypto')
const { readFileSync, writeFileSync } = require('node:fs')
const { performance } = require('node:perf_hooks')
const readline = require('node:readline')
const bundlePath = require.resolve('turndown')
const TurndownService = require(bundlePath)
const bundleHash = createHash('sha256').update(readFileSync(bundlePath)).digest('hex')

const inputs = new Map()

function benchmark (request) {
  if (!inputs.has(request.path)) {
    inputs.set(request.path, readFileSync(request.path, 'utf8'))
  }
  const html = inputs.get(request.path)
  const start = performance.now()
  const output = new TurndownService(request.options || {}).turndown(html)
  const elapsed = performance.now() - start
  const outputHash = createHash('sha256').update(output, 'utf8').digest('hex')
  if (request.output_path) writeFileSync(request.output_path, output, 'utf8')
  return {
    samples_ms: [elapsed],
    output_sha256: outputHash,
    output_bytes: Buffer.byteLength(output, 'utf8'),
    bundle_path: bundlePath,
    bundle_sha256: bundleHash,
    node_version: process.version,
    v8_version: process.versions.v8
  }
}

readline.createInterface({ input: process.stdin, crlfDelay: Infinity }).on('line', line => {
  try {
    console.log(JSON.stringify(benchmark(JSON.parse(line))))
  } catch (error) {
    console.log(JSON.stringify({ error: error.name, message: error.message }))
  }
})
