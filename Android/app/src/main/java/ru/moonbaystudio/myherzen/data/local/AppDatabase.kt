package ru.moonbaystudio.myherzen.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import ru.moonbaystudio.myherzen.data.local.dao.ScheduleDao
import ru.moonbaystudio.myherzen.data.local.entity.LocalScheduleCacheDay
import ru.moonbaystudio.myherzen.data.local.entity.LocalScheduleItem

@Database(entities = [LocalScheduleItem::class, LocalScheduleCacheDay::class], version = 2, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun scheduleDao(): ScheduleDao
}
