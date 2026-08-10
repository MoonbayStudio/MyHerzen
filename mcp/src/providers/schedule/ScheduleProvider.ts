import type {
  GetScheduleInput,
  GetScheduleResult,
  SearchGroupsResult,
} from "../../domain/schedule.js";

export interface ScheduleProvider {
  searchGroups(query: string): Promise<SearchGroupsResult>;
  getSchedule(input: GetScheduleInput): Promise<GetScheduleResult>;
}
