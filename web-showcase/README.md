# Fastest Route browser demonstration

Arrange up to seven supported New York City landmarks, compare their order, and export the result as CSV or open it in Maps. The browser uses geographic distance estimates. It does not calculate street routes, travel time, or live traffic.

The React/TypeScript implementation provides a small, inspectable route-ordering example with validated inputs and an explicit output. The separate Python application is described in [the parent README](../README.md). This demo's landmark dataset and distance model are deliberately limited; arbitrary addresses require a different geocoding and routing integration.

## Run and build

Use Node 22.22 or newer in the Node 22 series and npm. From this directory:

```bash
npm ci
npm run dev
```

Open the local URL printed by the server. `npm run build` produces the Sites deployment build; `npm run lint` checks the source. No API key is needed for the browser demonstration. Hosting configuration is in `.openai/hosting.json`; publishing is a separate step.
