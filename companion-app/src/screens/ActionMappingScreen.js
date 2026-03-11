/**
 * companion-app/src/screens/ActionMappingScreen.js
 *
 * Shows all labels the user has taught the AI and their mapped text actions.
 * Users can see, read current mappings, and the Pi URL can be updated from here.
 */

import React, { useState, useCallback } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, RefreshControl, TextInput
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getActionMappings } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Feather } from '@expo/vector-icons';

const COLORS = {
    bg: '#050814',
    cardBg: 'rgba(255, 255, 255, 0.03)',
    cardBorder: 'rgba(255, 255, 255, 0.1)',
    primary: '#00F0FF',
    accent: '#B026FF',
    success: '#00F0FF', 
    text: '#FFFFFF',
    textMuted: '#9CA3AF',
    textDark: '#111827',
};

export default function ActionMappingScreen({ navigation }) {
    const [mappings, setMappings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');

    const loadMappings = async (isRefresh = false) => {
        if (isRefresh) setRefresh(true);
        else setLoading(true);
        setError(null);
        try {
            const res = await getActionMappings();
            setMappings(res.data.mappings ?? []);
        } catch (e) {
            setError('System Offline.\nVerify Uplink IP in System tab.');
        } finally {
            setLoading(false);
            setRefresh(false);
        }
    };

    useFocusEffect(useCallback(() => { loadMappings(); }, []));

    const filtered = search.trim()
        ? mappings.filter(m =>
            m.label.toLowerCase().includes(search.toLowerCase()) ||
            (m.action ?? '').toLowerCase().includes(search.toLowerCase())
        )
        : mappings;

    const renderEmpty = () => {
        if (loading) return null;
        if (error) {
            return (
                <View style={styles.center}>
                    <Feather name="wifi-off" size={48} color={COLORS.textMuted} style={styles.emptyIcon} />
                    <Text style={styles.errorText}>{error}</Text>
                    <TouchableOpacity onPress={() => loadMappings()} style={styles.retryBtn}>
                        <LinearGradient colors={[COLORS.primary, '#00A3FF']} style={styles.btnGradient}>
                            <Text style={styles.retryText}>Re-establish Link</Text>
                        </LinearGradient>
                    </TouchableOpacity>
                </View>
            );
        }
        return (
            <View style={styles.center}>
                <Feather name="cpu" size={48} color={COLORS.textMuted} style={styles.emptyIcon} />
                <Text style={styles.emptyText}>
                    {search ? 'No matches found in neural net.' : 'Neural net is empty.\nInitiate physical Learn Mode.'}
                </Text>
            </View>
        );
    };

    const renderItem = ({ item }) => (
        <TouchableOpacity 
            activeOpacity={0.7}
            onPress={() => navigation.navigate('LabelDetails', { 
                label: item.label, 
                hasAction: item.has_action, 
                action: item.action 
            })}
        >
            <BlurView intensity={20} tint="dark" style={styles.card}>
                <View style={styles.cardRow}>
                    <View style={[styles.dot, { backgroundColor: item.has_action ? COLORS.success : COLORS.textMuted, shadowColor: item.has_action ? COLORS.success : 'transparent' }]} />
                    <View style={styles.cardContent}>
                        <Text style={styles.labelText}>{item.label}</Text>
                        {item.has_action ? (
                            <LinearGradient 
                                colors={['rgba(0, 240, 255, 0.15)', 'rgba(0, 240, 255, 0.05)']} 
                                style={styles.actionBadge}
                            >
                                <Feather name="zap" size={12} color={COLORS.primary} style={styles.actionIcon} />
                                <Text style={styles.actionText}>{item.action}</Text>
                            </LinearGradient>
                        ) : (
                            <Text style={styles.noAction}>Unassigned memory</Text>
                        )}
                    </View>
                    <Feather name="chevron-right" size={20} color={COLORS.textMuted} style={{ alignSelf: 'center' }} />
                </View>
            </BlurView>
        </TouchableOpacity>
    );

    return (
        <View style={styles.container}>
            {/* Background glowing orbs */}
            <View style={styles.glowTopLeft} />
            <View style={styles.glowBottomRight} />

            {/* Search bar */}
            <View style={styles.searchContainer}>
                <BlurView intensity={30} tint="dark" style={styles.searchRow}>
                    <Feather name="search" size={18} color={COLORS.textMuted} style={styles.searchIcon} />
                    <TextInput
                        style={styles.searchInput}
                        value={search}
                        onChangeText={setSearch}
                        placeholder="Search neural patterns..."
                        placeholderTextColor={COLORS.textMuted}
                    />
                    {search.length > 0 && (
                        <TouchableOpacity onPress={() => setSearch('')} style={styles.clearBtn}>
                            <Feather name="x" size={16} color={COLORS.textMuted} />
                        </TouchableOpacity>
                    )}
                </BlurView>
            </View>

            <FlatList
                contentContainerStyle={styles.list}
                data={filtered}
                keyExtractor={item => item.label}
                renderItem={renderItem}
                ListEmptyComponent={renderEmpty}
                refreshControl={
                    <RefreshControl
                        refreshing={refresh}
                        onRefresh={() => loadMappings(true)}
                        tintColor={COLORS.primary}
                    />
                }
                ListHeaderComponent={
                    filtered.length > 0 && (
                        <Text style={styles.countText}>
                            {filtered.length} pattern{filtered.length !== 1 ? 's' : ''} index | {filtered.filter(m => m.has_action).length} active
                        </Text>
                    )
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    glowTopLeft: { position: 'absolute', top: -100, left: -100, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(0, 240, 255, 0.12)', opacity: 0.8, blurRadius: 60 },
    glowBottomRight: { position: 'absolute', bottom: -50, right: -100, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(176, 38, 255, 0.12)', opacity: 0.8, blurRadius: 60 },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, marginTop: 100 },
    list: { paddingHorizontal: 16, paddingBottom: 120, paddingTop: 10 },
    countText: { fontFamily: 'Outfit_600SemiBold', fontSize: 11, color: COLORS.textMuted, marginVertical: 12, textTransform: 'uppercase', letterSpacing: 1.2 },
    searchContainer: { paddingHorizontal: 16, paddingTop: 100, paddingBottom: 10, zIndex: 10 },
    searchRow: { flexDirection: 'row', borderRadius: 16, borderWidth: 1, borderColor: COLORS.cardBorder, alignItems: 'center', paddingHorizontal: 16, height: 50, overflow: 'hidden' },
    searchIcon: { marginRight: 10 },
    searchInput: { flex: 1, color: COLORS.text, fontFamily: 'Outfit_400Regular', fontSize: 15 },
    clearBtn: { padding: 4 },
    card: { backgroundColor: COLORS.cardBg, borderRadius: 16, borderWidth: 1, borderColor: COLORS.cardBorder, marginBottom: 12, padding: 16, overflow: 'hidden' },
    cardRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 14 },
    dot: { width: 8, height: 8, borderRadius: 4, marginTop: 8, shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.8, shadowRadius: 6 },
    cardContent: { flex: 1, justifyContent: 'center' },
    labelText: { fontFamily: 'Outfit_800ExtraBold', fontSize: 17, color: COLORS.text, textTransform: 'capitalize', marginBottom: 6, letterSpacing: 0.3 },
    actionBadge: { flexDirection: 'row', alignItems: 'center', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 5, gap: 6, alignSelf: 'flex-start', borderWidth: 1, borderColor: 'rgba(0, 240, 255, 0.3)' },
    actionIcon: {},
    actionText: { fontFamily: 'Outfit_600SemiBold', fontSize: 12, color: COLORS.primary },
    noAction: { fontFamily: 'Outfit_400Regular', fontSize: 13, color: COLORS.textMuted, fontStyle: 'italic' },
    emptyIcon: { marginBottom: 16, opacity: 0.6 },
    emptyText: { fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, textAlign: 'center', lineHeight: 24, fontSize: 15 },
    errorText: { fontFamily: 'Outfit_600SemiBold', color: '#F87171', textAlign: 'center', lineHeight: 24, marginBottom: 20, fontSize: 15 },
    retryBtn: { overflow: 'hidden', borderRadius: 12 },
    btnGradient: { paddingHorizontal: 24, paddingVertical: 12 },
    retryText: { color: COLORS.textDark, fontFamily: 'Outfit_800ExtraBold', fontSize: 14, letterSpacing: 0.5 },
});
