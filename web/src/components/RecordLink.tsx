import { useContext } from 'react'
import { SOURCE_LABELS, type SourceName } from '../lib/format'
import { recordUrl, SlugsContext } from '../lib/links'
import type { Level } from './capabilities'

type Props = {
  level: Level
  value: { source: SourceName; source_id: string }
}

/** The record a value came from, linked to the source's page where possible. */
export function RecordLink({ level, value }: Props) {
  const url = recordUrl(level, value.source, value.source_id, useContext(SlugsContext))
  const title = `From ${SOURCE_LABELS[value.source]} record ${value.source_id}`
  return url
    ? <a className="record" href={url} target="_blank" rel="noreferrer" title={title}>{value.source_id}</a>
    : <span className="record" title={title}>{value.source_id}</span>
}
