import { runsClient, type RunsClient } from './runsClient';

/** A BacktestState loader that fetches a stored run by id. */
export function storedRunLoader(
  id: string,
  client: RunsClient = runsClient,
): () => Promise<unknown> {
  return () => client.getRun(id);
}
