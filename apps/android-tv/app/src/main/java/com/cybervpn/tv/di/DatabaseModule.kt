package com.cybervpn.tv.di

import android.app.Application
import androidx.room.Room
import com.cybervpn.tv.data.local.CyberVpnDatabase
import com.cybervpn.tv.data.local.dao.VpnDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideCyberVpnDatabase(app: Application): CyberVpnDatabase {
        return Room.databaseBuilder(
            app,
            CyberVpnDatabase::class.java,
            "cybervpn_tv.db",
        ).fallbackToDestructiveMigration().build()
    }

    @Provides
    @Singleton
    fun provideVpnDao(db: CyberVpnDatabase): VpnDao {
        return db.vpnDao
    }
}
