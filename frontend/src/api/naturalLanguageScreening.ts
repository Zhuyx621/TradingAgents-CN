import { ApiClient } from './request'

export interface ScreeningResultItem {
  code: string
  name: string
  industry?: string
  area?: string
  market?: string
  close?: number
  pct_chg?: number
  pe?: number
  pb?: number
  total_mv?: number
}

export interface AnalysisTaskItem {
  stock_code: string
  stock_name?: string
  task_id: string
}

export interface ScreeningCondition {
  field: string
  operator: string
  value: any
}

export interface ScreeningOrderBy {
  field: string
  direction: 'asc' | 'desc'
}

export interface NaturalLanguageScreeningRequest {
  query: string
  add_to_favorites?: boolean
  run_analysis?: boolean
  analysis_params?: {
    research_depth?: string
    analysts?: string[]
  }
}

export interface NaturalLanguageScreeningResponse {
  success: boolean
  description: string
  total_found: number
  screened_stocks: ScreeningResultItem[]
  added_to_favorites: string[]
  analysis_tasks: AnalysisTaskItem[]
  conditions: ScreeningCondition[]
  order_by: ScreeningOrderBy[]
  limit: number
  timestamp: string
}

export interface ParseQueryResponse {
  success: boolean
  description: string
  conditions: ScreeningCondition[]
  order_by: ScreeningOrderBy[]
  limit: number
}

export const naturalLanguageScreeningApi = {
  screen: (payload: NaturalLanguageScreeningRequest) =>
    ApiClient.post<NaturalLanguageScreeningResponse>('/api/nl-screening/screen', payload),

  parse: (query: string) =>
    ApiClient.post<ParseQueryResponse>('/api/nl-screening/parse', null, {
      params: { query }
    })
}
