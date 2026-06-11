package ru.moonbaystudio.myherzen.data.repository

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import ru.moonbaystudio.myherzen.data.local.dao.ScheduleDao
import ru.moonbaystudio.myherzen.data.local.entity.LocalScheduleItem
import ru.moonbaystudio.myherzen.data.model.Institute
import ru.moonbaystudio.myherzen.data.model.MyGroup
import ru.moonbaystudio.myherzen.data.model.ScheduleItem
import ru.moonbaystudio.myherzen.data.remote.HerzenApiService
import ru.moonbaystudio.myherzen.data.remote.MyHerzenApiService
import java.text.SimpleDateFormat
import java.util.Locale
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScheduleRepository @Inject constructor(
    private val apiService: HerzenApiService,
    private val myHerzenApiService: MyHerzenApiService,
    private val scheduleDao: ScheduleDao
) {
    private val requestDateFormatter = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    fun getScheduleFlow(groupId: Int, date: java.util.Date, examOnly: Boolean): Flow<List<ScheduleItem>> {
        val dateStr = requestDateFormatter.format(date)
        val flow = if (examOnly) {
            scheduleDao.getSession(groupId)
        } else {
            scheduleDao.getSchedule(groupId, dateStr)
        }
        return flow.map { localItems ->
            localItems.map { it.toDomain() }
        }
    }

    suspend fun getScheduleSync(groupId: Int, date: java.util.Date): List<ScheduleItem> {
        val dateStr = requestDateFormatter.format(date)
        return scheduleDao.getScheduleSync(groupId, dateStr).map { it.toDomain() }
    }

    suspend fun getHomeworks(groupId: Int, date: java.util.Date): List<ru.moonbaystudio.myherzen.data.remote.Homework> {
        val dateStr = requestDateFormatter.format(date)
        return try {
            val response = myHerzenApiService.getGroupHomeworks(groupId, dateStr)
            if (response.isSuccessful) {
                response.body() ?: emptyList()
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun createHomework(
        groupId: Int,
        lessonDate: String,
        lessonTime: String,
        subject: String,
        teacher: String?,
        room: String?,
        text: String
    ): Result<ru.moonbaystudio.myherzen.data.remote.Homework> {
        return try {
            val request = ru.moonbaystudio.myherzen.data.remote.HomeworkMutationRequest(
                lessonDate = lessonDate,
                lessonTime = lessonTime,
                subject = subject,
                teacher = teacher,
                room = room,
                text = text
            )
            val response = myHerzenApiService.createHomework(groupId, request)
            if (response.isSuccessful) {
                response.body()?.let { Result.success(it) } ?: Result.failure(Exception("Empty body"))
            } else {
                Result.failure(Exception("Error ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateHomework(
        groupId: Int,
        homeworkId: String,
        text: String
    ): Result<ru.moonbaystudio.myherzen.data.remote.Homework> {
        return try {
            val request = ru.moonbaystudio.myherzen.data.remote.HomeworkUpdateRequest(text)
            val response = myHerzenApiService.updateHomework(groupId, homeworkId, request)
            if (response.isSuccessful) {
                response.body()?.let { Result.success(it) } ?: Result.failure(Exception("Empty body"))
            } else {
                Result.failure(Exception("Error ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun deleteHomework(groupId: Int, homeworkId: String): Result<Unit> {
        return try {
            val response = myHerzenApiService.deleteHomework(groupId, homeworkId)
            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Error ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun refreshSchedule(groupId: Int, date: java.util.Date, examOnly: Boolean) {
        if (examOnly) {
            val calendar = java.util.Calendar.getInstance()
            calendar.time = date
            calendar.add(java.util.Calendar.DAY_OF_YEAR, -120)
            val startDate = calendar.time
            calendar.time = date
            calendar.add(java.util.Calendar.DAY_OF_YEAR, 120)
            val endDate = calendar.time
            refreshScheduleRange(groupId, startDate, endDate, true)
        } else {
            refreshScheduleRange(groupId, date, date, false)
        }
    }

    suspend fun fetchSchedule(groupId: Int, date: java.util.Date, examOnly: Boolean): List<ScheduleItem> {
        val dateStr = requestDateFormatter.format(date)
        val lessons = apiService.getSchedule(groupId, dateStr, dateStr, examOnly)
        return lessonsToDomain(groupId, lessons, examOnly).map { it.toDomain() }
    }

    private suspend fun lessonsToDomain(groupId: Int, lessons: List<ru.moonbaystudio.myherzen.data.remote.ScheduleResponseDto>, examOnly: Boolean): List<LocalScheduleItem> {
        val teacherIds = lessons.mapNotNull { it.teacherId }.distinct().joinToString(",")
        val roomIds = lessons.mapNotNull { it.roomId }.distinct().joinToString(",")
        
        val teachers = if (teacherIds.isNotEmpty()) apiService.getTeachers(teacherIds).associateBy { it.id } else emptyMap()
        val rooms = if (roomIds.isNotEmpty()) apiService.getRooms(roomIds).associateBy { it.id } else emptyMap()
        
        val buildingIds = rooms.values.mapNotNull { it.buildingId }.distinct().joinToString(",")
        val buildings = if (buildingIds.isNotEmpty()) apiService.getBuildings(buildingIds).associateBy { it.id } else emptyMap()

        return lessons.map { lesson ->
            val teacherName = teachers[lesson.teacherId]?.name ?: ""
            val roomName = rooms[lesson.roomId]?.name ?: ""
            val address = rooms[lesson.roomId]?.buildingId?.let { buildings[it]?.name } ?: ""
            val lessonDate = lesson.startTime.substringBefore("T")
            
            LocalScheduleItem(
                id = "${lesson.startTime}_${lesson.name}_${teacherName}_${address}_${lesson.type}_${roomName}_${lesson.subGroupId ?: ""}",
                groupId = groupId,
                date = lessonDate,
                sortDateIso = lesson.startTime,
                endDateIso = lesson.endTime,
                time = formatTimeRange(lesson.startTime, lesson.endTime),
                title = lesson.name,
                teacher = teacherName,
                lessonType = lesson.type,
                address = address,
                subgroup = lesson.subGroupId?.toString(),
                period = if (examOnly) lessonDate else "",
                room = roomName,
                classUrl = lesson.classUrl
            )
        }
    }

    suspend fun refreshScheduleRange(groupId: Int, startDate: java.util.Date, endDate: java.util.Date, examOnly: Boolean) {
        val startDateStr = requestDateFormatter.format(startDate)
        val endDateStr = requestDateFormatter.format(endDate)
        
        val lessons = apiService.getSchedule(groupId, startDateStr, endDateStr, examOnly)
        val localItems = lessonsToDomain(groupId, lessons, examOnly)
        
        if (examOnly) {
            scheduleDao.updateSession(groupId, localItems)
        } else {
            // Update each day in range
            val calendar = java.util.Calendar.getInstance()
            calendar.time = startDate
            while (!calendar.time.after(endDate)) {
                val d = requestDateFormatter.format(calendar.time)
                val itemsForDay = localItems.filter { it.date == d }
                scheduleDao.updateSchedule(groupId, d, itemsForDay)
                calendar.add(java.util.Calendar.DAY_OF_YEAR, 1)
            }
        }
    }

    suspend fun clearCache(groupId: Int) {
        scheduleDao.deleteScheduleBefore(groupId, "9999-99-99") // Delete all
        scheduleDao.deleteSession(groupId)
    }

    suspend fun hasDataForDate(groupId: Int, date: java.util.Date): Boolean {
        return scheduleDao.hasDataForDate(groupId, requestDateFormatter.format(date))
    }

    suspend fun hasSession(groupId: Int): Boolean {
        return scheduleDao.hasSession(groupId)
    }

    suspend fun getMaxCachedDate(groupId: Int): java.util.Date? {
        return scheduleDao.getMaxDate(groupId)?.let { requestDateFormatter.parse(it) }
    }

    suspend fun getMinCachedDate(groupId: Int): java.util.Date? {
        return scheduleDao.getMinDate(groupId)?.let { requestDateFormatter.parse(it) }
    }

    suspend fun cleanOldCache(groupId: Int, currentDate: java.util.Date) {
        val calendar = java.util.Calendar.getInstance()
        calendar.time = currentDate
        // Move to the beginning of the previous week
        calendar.set(java.util.Calendar.DAY_OF_WEEK, calendar.firstDayOfWeek)
        calendar.add(java.util.Calendar.WEEK_OF_YEAR, -1)
        val limitDate = requestDateFormatter.format(calendar.time)
        scheduleDao.deleteScheduleBefore(groupId, limitDate)
    }

    suspend fun getInstitutesWithGroups(): List<Institute> {
        val faculties = apiService.getFaculties()
        val groups = apiService.getGroups()

        val facultyMap = faculties.associateBy { it.id }
        
        return groups.groupBy { it.facultyId }
            .map { (facultyId, facultyGroups) ->
                val facultyName = facultyMap[facultyId]?.name ?: "Институт $facultyId"
                Institute(
                    id = facultyId.toString(),
                    name = facultyName,
                    groups = facultyGroups.map { MyGroup(it.id.toString(), it.name) }
                        .sortedBy { it.name }
                )
            }
            .sortedBy { it.name }
    }

    private fun formatTimeRange(start: String, end: String): String {
        val startTime = start.substringAfter("T").take(5)
        val endTime = end.substringAfter("T").take(5)
        return "$startTime-$endTime"
    }

    private fun LocalScheduleItem.toDomain(): ScheduleItem {
        return ScheduleItem(
            id = id,
            sortDateIso = sortDateIso,
            endDateIso = endDateIso,
            time = time,
            title = title,
            teacher = teacher,
            lessonType = lessonType,
            address = address,
            subgroup = subgroup,
            period = period,
            room = room,
            classUrl = classUrl
        )
    }
}
