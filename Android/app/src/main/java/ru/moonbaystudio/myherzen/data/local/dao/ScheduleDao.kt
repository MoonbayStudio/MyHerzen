package ru.moonbaystudio.myherzen.data.local.dao

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import ru.moonbaystudio.myherzen.data.local.entity.LocalScheduleItem

@Dao
interface ScheduleDao {
    @Query("SELECT * FROM schedule_items WHERE groupId = :groupId AND date = :date AND period = ''")
    fun getSchedule(groupId: Int, date: String): Flow<List<LocalScheduleItem>>

    @Query("SELECT * FROM schedule_items WHERE groupId = :groupId AND date = :date AND period = '' ORDER BY sortDateIso ASC")
    suspend fun getScheduleSync(groupId: Int, date: String): List<LocalScheduleItem>

    @Query("SELECT * FROM schedule_items WHERE groupId = :groupId AND period != ''")
    fun getSession(groupId: Int): Flow<List<LocalScheduleItem>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<LocalScheduleItem>)

    @Query("DELETE FROM schedule_items WHERE groupId = :groupId AND date = :date AND period = ''")
    suspend fun deleteSchedule(groupId: Int, date: String)

    @Query("DELETE FROM schedule_items WHERE groupId = :groupId AND date < :date AND period = ''")
    suspend fun deleteScheduleBefore(groupId: Int, date: String)

    @Query("SELECT MAX(date) FROM schedule_items WHERE groupId = :groupId AND period = ''")
    suspend fun getMaxDate(groupId: Int): String?

    @Query("SELECT MIN(date) FROM schedule_items WHERE groupId = :groupId AND period = ''")
    suspend fun getMinDate(groupId: Int): String?

    @Query("SELECT EXISTS(SELECT 1 FROM schedule_items WHERE groupId = :groupId AND date = :date AND period = '')")
    suspend fun hasDataForDate(groupId: Int, date: String): Boolean

    @Query("SELECT EXISTS(SELECT 1 FROM schedule_items WHERE groupId = :groupId AND period != '')")
    suspend fun hasSession(groupId: Int): Boolean

    @Query("DELETE FROM schedule_items WHERE groupId = :groupId AND period != ''")
    suspend fun deleteSession(groupId: Int)

    @Transaction
    suspend fun updateSchedule(groupId: Int, date: String, items: List<LocalScheduleItem>) {
        deleteSchedule(groupId, date)
        insertAll(items)
    }

    @Transaction
    suspend fun updateSession(groupId: Int, items: List<LocalScheduleItem>) {
        deleteSession(groupId)
        insertAll(items)
    }
}
