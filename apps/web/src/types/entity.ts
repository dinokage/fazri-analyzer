// types/entity.ts
export interface Identifier {
  type: string;
  value: string;
  source: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
}

export interface Entity {
  entity_id: string;
  identifiers: Identifier[];
  name: string | null;
  email: string | null;
  entity_type: string | null;
  department: string | null;
  linked_entity_ids: string[];
  confidence_score: number;
  created_at: string;
  updated_at: string;
}

export interface EntitySearchRequest {
  identifier_type: string;
  identifier_value: string;
}

export interface EntitySearchResponse {
  entity: Entity | null;
  all_identifiers: Record<string, object[]>;
  linked_entities: Entity[];
  confidence: number;
}