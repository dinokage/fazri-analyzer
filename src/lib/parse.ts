import Papa from "papaparse"


import {parseISO} from "date-fns" 
import { prisma } from "./db"

type Entity = {
    id: string,
    name: string,
    role: string,
    email: string,
    department: string,
    face_id: string,
    enroll_id: string,
    device_hash: string,
    card_id: string 
}

type Note = {
    id: string,
    entity_id: string,
    category:string,
    text:string,
    timestamp: Date
}

type Booking = {
    id: string,
    entity_id: string,
    room_id:string,
    start_time:Date,
    end_time:Date,
    attended: "YES" | "NO"
}

type CardSwipe = {
    id: string,
    location_id: string,
    timestamp: Date
}

type LibraryCheckout = {
    id:string,
    entity_id:string,
    book_id:string,
    timestamp:Date,
}

type WifiLogs = {
    device_hash: string,
    ap_id: string,
    timestamp: Date
}

type CCTVLogs = {
    id:string,
    location_id:string,
    timestamp:Date,
    face_id: string | null
}

const parseCSV = (csv: string) => {
    const result = Papa.parse(csv, {
        header:true,
        skipEmptyLines:true,
    })

    const data:any = result.data;
    return data
}

export const parseEntityData = (csv: string): Entity[] =>{
    const data = parseCSV(csv)
    const entityData:Entity[] = []
    for(let entity of data){
        entityData.push({
            id:entity.entity_id ,
            name: entity.name,
            role: entity.role,
            email: entity.email,
            department: entity.department,
            face_id: entity.face_id,
            enroll_id: entity.role ==="student"? entity.student_id: entity.staff_id,
            device_hash: entity.device_hash,
            card_id: entity.card_id
        })
    }


    return entityData
}

export const parseNoteData = (csv:string): Note[] => {
    const data = parseCSV(csv)
    const noteData: Note[] = []
    for(let note of data){
        noteData.push({
            id:note.note_id,
            entity_id:note.entity_id,
            category: note.category,
            text: note.text,
            timestamp:parseISO(note.timestamp)
        })
    }

    return noteData
}

export const parseBookingData = (csv:string): Booking[] =>{
    const data = parseCSV(csv)
    const bookingData: Booking[] = []

    for(let booking of data){
        const attended = booking['attended (YES/NO)'] || booking['attended']
        bookingData.push({
            id:booking.booking_id,
            entity_id:booking.entity_id,
            room_id:booking.room_id,
            start_time:new Date(booking.start_time),
            end_time:new Date(booking.end_time),
            attended:attended
        })
    }
    return bookingData
}

export const parseCardSwipeData = (csv:string): CardSwipe[] =>{
    const data = parseCSV(csv)
    const cardSwipeData: CardSwipe[] = []

    for(let cardswipe of data){
        cardSwipeData.push({
            id:cardswipe.card_id,
            location_id:cardswipe.location_id,
            timestamp:new Date(cardswipe.timestamp)
        })
    }
    return cardSwipeData 
}

export const parseLibraryCheckoutData = (csv:string): LibraryCheckout[] =>{
    const data = parseCSV(csv)
    const libraryCheckoutData: LibraryCheckout[] = []

    for(let libraryCheckout of data){
        libraryCheckoutData.push({
            id:libraryCheckout.checkout_id,
            entity_id:libraryCheckout.entity_id,
            book_id:libraryCheckout.book_id,
            timestamp:new Date(libraryCheckout.timestamp)
        })
    }
    return libraryCheckoutData 
}

export const parseWifiLogsData = (csv:string): WifiLogs[] =>{
    const data = parseCSV(csv)
    const wifiLogsData: WifiLogs[] = []

    for(let wifiLogs of data){
        wifiLogsData.push({
            device_hash:wifiLogs.device_hash,
            ap_id:wifiLogs.ap_id,
            timestamp:new Date(wifiLogs.timestamp)
        })
    }
    return wifiLogsData 
}

export const parseCCTVLogsData = (csv:string): CCTVLogs[] =>{
    const data = parseCSV(csv)
    const CCTVLogsData: CCTVLogs[] = []

    for(let CCTVLogs of data){
        CCTVLogsData.push({
            id: CCTVLogs.frame_id,
            location_id: CCTVLogs.location_id,
            timestamp: new Date(CCTVLogs.timestamp),
            face_id: CCTVLogs.face_id
        })
    }
    return CCTVLogsData 
}


export const createEntityRecords = async (data:Entity[]) => {
    const result = await prisma.entity.createMany({
        data:data
    }) 

    return result
}

export const createAuditNoteRecords = async (data:Note[]) => {
    const entities = await prisma.entity.findMany({
        where:{
            id:{
                in:data.map((note) => note.entity_id)
            }
        }
    })

    const auditLogs = await prisma.auditLog.createMany({
        data:data.map((note) => ({
            entity_id: entities.find(entity => entity.id === note.entity_id)?.id,
            
        }))
    })
}