package ru.moonbaystudio.myherzen.service

import ru.moonbaystudio.myherzen.data.model.ScheduleItem
import ru.moonbaystudio.myherzen.data.repository.ScheduleRepository
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScheduleLiveStateManager @Inject constructor(
    private val repository: ScheduleRepository
) {
    private val isoFormatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)

    suspend fun getCurrentState(groupId: Int): ScheduleLiveState {
        val now = Date()
        val calendar = Calendar.getInstance()
        calendar.time = now
        
        // We only care about lessons for today
        val lessons = repository.getScheduleSync(groupId, now)
        
        if (lessons.isEmpty()) {
            val hasData = repository.hasDataForDate(groupId, now)
            return if (hasData) ScheduleLiveState.NoLessons else ScheduleLiveState.NoCache
        }

        // Sort by start time just in case
        val sortedLessons = lessons.sortedBy { it.sortDateIso }

        for (i in sortedLessons.indices) {
            val lesson = sortedLessons[i]
            val startTime = isoFormatter.parse(lesson.sortDateIso!!) ?: continue
            val endTime = isoFormatter.parse(lesson.endDateIso!!) ?: continue

            if (now.before(startTime)) {
                // If it's before the first lesson or between lessons (break)
                return if (i == 0) {
                    ScheduleLiveState.BeforeLessons(lesson)
                } else {
                    ScheduleLiveState.Break(lesson)
                }
            } else if (now.after(startTime) && now.before(endTime)) {
                // Currently in lesson
                val progress = (now.time - startTime.time).toFloat() / (endTime.time - startTime.time).toFloat()
                val nextLesson = if (i + 1 < sortedLessons.size) sortedLessons[i + 1] else null
                return ScheduleLiveState.Lesson(lesson, nextLesson, progress)
            }
        }

        return ScheduleLiveState.AfterLessons
    }
}
